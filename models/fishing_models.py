from odoo import models, fields, api, exceptions
import base64
import io
from datetime import date, timedelta
import matplotlib.pyplot as plt

class FishingZoneLog(models.Model):
    """Bitácora de Actividad en Zona.

    Registra eventos relacionados con una zona pesquera: entradas, salidas
    y reportes de captura. Contiene campos de referencia a la zona y al
    navío, tipo de actividad y datos de captura cuando aplique.
    """
    _name = 'fishing.zone.log'
    _description = 'Bitácora de Actividad en Zona'
    _order = 'date desc' # Ordenar por fecha, lo más reciente primero

    zone_id = fields.Many2one('fishing.zone', string='Zona Pesquera', required=True, ondelete='cascade')
    vessel_id = fields.Many2one('fishing.vessel', string='Navío', required=True)
    date = fields.Datetime(string='Fecha y Hora', default=fields.Datetime.now, required=True)
    
    activity_type = fields.Selection([
        ('entry', 'Entrada a Zona'),
        ('exit', 'Salida de Zona'),
        ('capture', 'Reporte de Captura')
    ], string='Tipo de Actividad', required=True)

    # Campos específicos para la captura (opcionales si es solo entrada/salida)
    species = fields.Selection([
        ('anchovy', 'Anchoa'),
        ('sardine', 'Sardina'),
        ('mackerel', 'Caballa'),
        ('tuna', 'Atún'),
        ('cod', 'Bacalao')
    ], string='Especie Capturada')
    
    catch_kg = fields.Float(string='Captura (Kg)')

class FishingZone(models.Model):
    """Representa una zona pesquera.

    Almacena información geográfica y tipificación de la zona, además de
    relaciones inversas a navíos y registros de bitácora asociados.
    """
    _name = 'fishing.zone'
    _description = 'Zona Pesquera'

    name = fields.Char(string='Nombre de la Zona', required=True)
    code = fields.Char(string='Código de Zona')
    latitude = fields.Float(string='Latitud Centro', digits=(10, 7))
    longitude = fields.Float(string='Longitud Centro', digits=(10, 7))
    zone_type = fields.Selection([
        ('coast', 'Costera'),
        ('deep_sea', 'Alta Mar'),
        ('restricted', 'Restringida')
    ], string='Tipo de Zona', required=True)
    active = fields.Boolean(default=True)

    vessel_ids = fields.One2many(
        'fishing.vessel', 
        'current_zone_id', 
        string='Navíos en la Zona'
    )
    log_ids = fields.One2many(
        'fishing.zone.log', 
        'zone_id', 
        string='Bitácora de Actividades'
    )

class FishingVessel(models.Model):
    """Modelo que representa un navío pesquero.

    Incluye información identificativa, estado operativo y ubicación,
    además de automatización para crear eventos en la bitácora cuando
    cambia la zona actual del navío.
    """
    _name = 'fishing.vessel'
    _description = 'Navío Pesquero'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Nombre del Navío', required=True, tracking=True)
    license_plate = fields.Char(string='Matrícula', required=True)
    captain_id = fields.Many2one('res.partner', string='Capitán')
    capacity_kg = fields.Float(string='Capacidad de Bodega (Kg)')
    
    state = fields.Selection([
        ('docked', 'En Muelle'),
        ('fishing', 'En Faena'),
        ('maintenance', 'Mantenimiento')
    ], string='Estado', default='docked', tracking=True)

    lasted_viaje_date = fields.Date(
        string='Fecha del Último Viaje (Histórico)', 
        default=fields.Date.context_today
    )
    lasted_viaje_ubication = fields.Char(string='Ubicación Texto')
    
    current_zone_id = fields.Many2one(
        'fishing.zone', 
        string='Zona Actual / Destino',
        tracking=True
    )

    last_departure_datetime = fields.Datetime(string='Fecha y Hora de Zarpe', tracking=True)
    
    current_latitude = fields.Float(string='Latitud Actual', digits=(10, 7))
    current_longitude = fields.Float(string='Longitud Actual', digits=(10, 7))

    # Nuevo campo calculado para controlar la visibilidad del botón
    can_report_capture = fields.Boolean(
        string='Puede Reportar Captura',
        compute='_compute_can_report_capture',
        store=False, # No guardar en BD, solo se calcula al vuelo
    )
    
    @api.depends('state')
    def _compute_can_report_capture(self):
        """ Determina si el navío está en estado 'fishing' (En Faena) """
        for vessel in self:
            vessel.can_report_capture = (vessel.state == 'fishing')


    # --- LÓGICA DE AUTOMATIZACIÓN DE BITÁCORA ---

    @api.model
    def create(self, vals):
        record = super(FishingVessel, self).create(vals)
        
        # Si se crea con una zona asignada, registra una entrada
        if record.current_zone_id:
            record._register_zone_change(record.current_zone_id.id, activity_type='entry')
            
        return record

    def write(self, vals):
        # 1. Detectar si se está cambiando la zona actual.
        if 'current_zone_id' in vals:
            old_zone_id = self.current_zone_id.id
            new_zone_id = vals['current_zone_id']
            
            # 2. Primero, llamar al write original para actualizar el registro.
            result = super(FishingVessel, self).write(vals)

            # 3. Registrar la salida de la zona anterior (si existía y era diferente a la nueva).
            if old_zone_id and old_zone_id != new_zone_id:
                self._register_zone_change(old_zone_id, activity_type='exit')

            # 4. Registrar la entrada a la nueva zona (si existe y era diferente a la anterior).
            if new_zone_id and old_zone_id != new_zone_id:
                self._register_zone_change(new_zone_id, activity_type='entry')
                
            return result
        else:
            # Si no se cambia la zona, simplemente llamar al write original.
            return super(FishingVessel, self).write(vals)

    def _register_zone_change(self, zone_id, activity_type):
        """
        Método para crear un registro en la bitácora (fishing.zone.log) para entrada/salida.
        """
        log_obj = self.env['fishing.zone.log']
        
        for vessel in self:
            log_vals = {
                'zone_id': zone_id,
                'vessel_id': vessel.id,
                'activity_type': activity_type,
                'date': fields.Datetime.now(),
            }
            log_obj.create(log_vals)

    # ----------------------------------------------------
    
    @api.onchange('current_zone_id')
    def _onchange_current_zone_id(self):
        self.current_latitude=False
        self.current_longitude=False
        
        """
        Si se selecciona una zona, se copian sus coordenadas al navío.
        """
        if self.current_zone_id:
            self.current_latitude = self.current_zone_id.latitude
            self.current_longitude = self.current_zone_id.longitude

    image = fields.Image(string="Foto del Navío")
    tripulation_size = fields.Integer(string='Tamaño de la Tripulación')

class FishingShoal(models.Model):
    """Registro de avistamientos de cardúmenes (shoals).

    Permite documentar especie, tonaje estimado, fecha y ubicación del avistamiento.
    """
    _name = 'fishing.shoal'
    _description = 'Registro de Cardumen'

    name = fields.Char(string='Identificador', required=True, default=lambda self: ('Nuevo'))
    species = fields.Selection([
        ('anchovy', 'Anchoa'),
        ('sardine', 'Sardina'),
        ('mackerel', 'Caballa'),
        ('tuna', 'Atún'),
        ('cod', 'Bacalao')
    ], string='Especie', required=True)
    estimated_tonnage = fields.Float(string='Tonelaje Estimado')
    observation_date = fields.Datetime(string='Fecha de Avistamiento', default=fields.Datetime.now)
    
    zone_id = fields.Many2one('fishing.zone', string='Zona de Avistamiento')
    spotted_by_vessel_id = fields.Many2one('fishing.vessel', string='Avistado por Navío')
    
    notes = fields.Text(string='Notas Oceanográficas')

    @api.model
    def create(self, vals):
        if vals.get('name', 'Nuevo') == 'Nuevo':
            vals['name'] = self.env['ir.sequence'].next_by_code('fishing.shoal') or 'CARDUMEN'
        return super(FishingShoal, self).create(vals)

class FishingCaptureWizard(models.TransientModel):
    """Wizard (TransientModel) para reportar capturas desde un navío.

    Facilita la creación de un registro de tipo 'capture' en la bitácora
    asociándolo al navío y zona seleccionados por el usuario.
    """
    _name = 'fishing.capture.wizard'
    _description = 'Wizard para Reportar Captura'

    vessel_id = fields.Many2one(
        'fishing.vessel', 
        string='Navío', 
        required=True, 
        default=lambda self: self.env.context.get('active_id')
    )
    
    current_zone_id = fields.Many2one(
        'fishing.zone', 
        string='Zona de Reporte',
        required=True,
        compute='_compute_zone',
        store=True,
        readonly=False # Permitir al usuario cambiarla si es necesario
    )

    species = fields.Selection([
        ('anchovy', 'Anchoa'),
        ('sardine', 'Sardina'),
        ('mackerel', 'Caballa'),
        ('tuna', 'Atún'),
        ('cod', 'Bacalao')
    ], string='Especie Capturada', required=True)
    
    catch_kg = fields.Float(string='Captura (Kg)', required=True)

    @api.depends('vessel_id')
    def _compute_zone(self):
        """ Copia la zona actual del navío como zona de reporte por defecto. """
        for record in self:
            record.current_zone_id = record.vessel_id.current_zone_id.id
            
    def action_register_capture(self):
        """ 
        Función que es llamada por el botón del wizard.
        Crea el registro de Bitácora (fishing.zone.log).
        """
        self.ensure_one()
        
        # 1. Validación simple para asegurar que hay zona.
        if not self.current_zone_id:
            raise exceptions.UserError('Debe especificar una Zona de Reporte.')

        # 2. Crear el registro en la bitácora
        log_vals = {
            'zone_id': self.current_zone_id.id,
            'vessel_id': self.vessel_id.id,
            'activity_type': 'capture',
            'species': self.species,
            'catch_kg': self.catch_kg,
            'date': fields.Datetime.now(),
        }
        self.env['fishing.zone.log'].create(log_vals)
        
        # 3. (Opcional) Retornar una acción para refrescar la vista.
        return {'type': 'ir.actions.act_window_close'}

class FishingReportWizard(models.TransientModel):
    """Wizard para generar reportes gráficos y datos agregados de capturas.

    Permite filtrar por fechas, zona y especie y genera una imagen en base64
    con la gráfica correspondiente, además de un resumen de texto.
    """
    _name = 'fishing.report.wizard'
    _description = 'Wizard para Generar Reportes Gráficos'

    # Campos para filtros
    date_from = fields.Date(string='Desde', required=True, default=date.today() - timedelta(days=30))
    date_to = fields.Date(string='Hasta', required=True, default=fields.Date.context_today)
    zone_id = fields.Many2one('fishing.zone', string='Zona Pesquera')
    species = fields.Selection([
        ('anchovy', 'Anchoa'),
        ('sardine', 'Sardina'),
        ('mackerel', 'Caballa'),
        ('tuna', 'Atún'),
        ('cod', 'Bacalao')
    ], string='Especie')
    report_type = fields.Selection([
        ('capture_by_species', 'Captura por Especie'),
        ('capture_by_zone', 'Captura por Zona'),
        ('vessel_activity', 'Actividad de Navíos'),
        ('monthly_summary', 'Resumen Mensual')
    ], string='Tipo de Reporte', required=True, default='capture_by_species')
    
    # Campos para resultados
    report_image = fields.Binary(string='Gráfica', readonly=True)
    report_filename = fields.Char(string='Nombre del archivo')
    report_data = fields.Text(string='Datos del Reporte', readonly=True)

    def generate_report(self):
        self.ensure_one()
        
        # Crear dominio de búsqueda
        domain = [
            ('activity_type', '=', 'capture'),
            ('date', '>=', self.date_from),
            ('date', '<=', self.date_to)
        ]
        
        if self.zone_id:
            domain.append(('zone_id', '=', self.zone_id.id))
        if self.species:
            domain.append(('species', '=', self.species))

        # Obtener registros
        logs = self.env['fishing.zone.log'].search(domain)
        
        if not logs:
            raise exceptions.UserError('No hay datos para los filtros seleccionados.')
        
        # Generar gráfico según tipo
        if self.report_type == 'capture_by_species':
            image_data = self._generate_capture_by_species(logs)
        elif self.report_type == 'capture_by_zone':
            image_data = self._generate_capture_by_zone(logs)
        elif self.report_type == 'vessel_activity':
            image_data = self._generate_vessel_activity(logs)
        elif self.report_type == 'monthly_summary':
            image_data = self._generate_monthly_summary(logs)
        else:
            image_data = b''
        
        # Guardar resultados
        filename = f"reporte_{self.report_type}_{fields.Date.context_today(self)}.png"
        self.write({
            'report_image': image_data,
            'report_filename': filename,
            'report_data': self._generate_report_data(logs)
        })
        
        return {
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }

    def _generate_capture_by_species(self, logs):
        """Genera gráfico de torta de capturas por especie"""
        catch_by_species = {}
        for log in logs:
            species_name = dict(log._fields['species'].selection).get(log.species, log.species)
            if species_name not in catch_by_species:
                catch_by_species[species_name] = 0
            catch_by_species[species_name] += log.catch_kg
        
        # Crear gráfico
        plt.figure(figsize=(15, 10))
        if catch_by_species:
            labels = list(catch_by_species.keys())
            sizes = list(catch_by_species.values())
            colors = plt.cm.Paired(range(len(labels)))
            
            plt.pie(sizes, labels=labels, colors=colors, autopct='%1.1f%%', startangle=90)
            plt.axis('equal')
            plt.title(f'Distribución de Capturas por Especie\n{self.date_from} - {self.date_to}')
        else:
            plt.text(0.5, 0.5, 'No hay datos', ha='center', va='center')
        
        return self._save_plot_to_binary()

    def _generate_capture_by_zone(self, logs):
        """Genera gráfico de barras de capturas por zona"""
        catch_by_zone = {}
        for log in logs:
            zone_name = log.zone_id.name if log.zone_id else 'Sin zona'
            if zone_name not in catch_by_zone:
                catch_by_zone[zone_name] = 0
            catch_by_zone[zone_name] += log.catch_kg
        
        # Crear gráfico
        plt.figure(figsize=(12, 6))
        if catch_by_zone:
            zones = list(catch_by_zone.keys())
            catches = list(catch_by_zone.values())
            colors = plt.cm.viridis(range(len(zones)))
            
            bars = plt.bar(zones, catches, color=colors)
            plt.xlabel('Zona Pesquera')
            plt.ylabel('Captura Total (Kg)')
            plt.title(f'Capturas por Zona Pesquera\n{self.date_from} - {self.date_to}')
            plt.xticks(rotation=45, ha='right')
            
            # Añadir valores en las barras
            for bar, catch in zip(bars, catches):
                plt.text(bar.get_x() + bar.get_width()/2, bar.get_height(),
                        f'{catch:,.0f}', ha='center', va='bottom')
        else:
            plt.text(0.5, 0.5, 'No hay datos', ha='center', va='center')
        
        plt.tight_layout()
        return self._save_plot_to_binary()

    def _generate_vessel_activity(self, logs):
        """Genera gráfico de actividad de navíos"""
        activity_by_vessel = {}
        for log in logs:
            vessel_name = log.vessel_id.name if log.vessel_id else 'Sin navío'
            if vessel_name not in activity_by_vessel:
                activity_by_vessel[vessel_name] = 0
            activity_by_vessel[vessel_name] += 1  # Contar número de registros
        
        # Crear gráfico
        plt.figure(figsize=(12, 6))
        if activity_by_vessel:
            vessels = list(activity_by_vessel.keys())
            activities = list(activity_by_vessel.values())
            colors = plt.cm.viridis(range(len(vessels)))
            
            bars = plt.bar(vessels, activities, color=colors)
            plt.xlabel('Navío')
            plt.ylabel('Número de Registros de Captura')
            plt.title(f'Actividad de Navíos\n{self.date_from} - {self.date_to}')
            plt.xticks(rotation=45, ha='right')
        else:
            plt.text(0.5, 0.5, 'No hay datos', ha='center', va='center')
        
        plt.tight_layout()
        return self._save_plot_to_binary()

    def _generate_monthly_summary(self, logs):
        """Genera gráfico de líneas con tendencia mensual"""
        # Agrupar por mes
        monthly_data = {}
        for log in logs:
            month_key = log.date.strftime('%Y-%m')
            if month_key not in monthly_data:
                monthly_data[month_key] = 0
            monthly_data[month_key] += log.catch_kg
        
        # Ordenar por fecha
        sorted_months = sorted(monthly_data.items())
        months = [m[0] for m in sorted_months]
        catches = [m[1] for m in sorted_months]
        
        # Crear gráfico
        plt.figure(figsize=(12, 6))
        if months:
            plt.plot(months, catches, marker='o', linewidth=2, markersize=8, color='green')
            plt.xlabel('Mes')
            plt.ylabel('Captura Total (Kg)')
            plt.title(f'Tendencia Mensual de Capturas\n{self.date_from} - {self.date_to}')
            plt.xticks(rotation=45, ha='right')
            plt.grid(True, alpha=0.3)
            
            # Añadir valores en los puntos
            for x, y in zip(months, catches):
                plt.text(x, y, f'{y:,.0f}', ha='center', va='bottom')
        else:
            plt.text(0.5, 0.5, 'No hay datos', ha='center', va='center')
        
        plt.tight_layout()
        return self._save_plot_to_binary()

    def _generate_report_data(self, logs):
        """Genera texto con datos del reporte"""
        total_catch = sum(log.catch_kg for log in logs)
        avg_catch = total_catch / len(logs) if logs else 0
        
        data = f"""
        RESUMEN DEL REPORTE
        Período: {self.date_from} - {self.date_to}
        Total registros: {len(logs)}
        Captura total: {total_catch:,.2f} Kg
        Captura promedio: {avg_catch:,.2f} Kg
        Zona: {self.zone_id.name if self.zone_id else 'Todas'}
        Especie: {dict(self._fields['species'].selection).get(self.species, 'Todas')}
        
        DETALLE POR ESPECIE:
        """
        
        # Agrupar por especie
        by_species = {}
        for log in logs:
            if log.species not in by_species:
                by_species[log.species] = {'count': 0, 'total': 0}
            by_species[log.species]['count'] += 1
            by_species[log.species]['total'] += log.catch_kg
        
        for species, data_dict in by_species.items():
            species_name = dict(self._fields['species'].selection).get(species, species)
            data += f"\n  {species_name}: {data_dict['total']:,.2f} Kg ({data_dict['count']} registros)"
        
        return data

    def _save_plot_to_binary(self):
        """Guarda el gráfico en binario"""
        buffer = io.BytesIO()
        plt.savefig(buffer, format='png', dpi=150, bbox_inches='tight')
        buffer.seek(0)
        image_data = base64.b64encode(buffer.read())
        plt.close()  # Cerrar la figura para liberar memoria
        return image_data

    def download_report(self):
        """Descarga el reporte como imagen"""
        self.ensure_one()
        
        if not self.report_image:
            raise exceptions.UserError('Primero debe generar el reporte.')
        
        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/fishing.report.wizard/{self.id}/report_image/{self.report_filename}?download=true',
            'target': 'self',
        }