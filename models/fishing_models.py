import matplotlib
matplotlib.use('Agg')  # DEBE ESTAR ANTES de importar plt
from odoo import models, fields, api, exceptions
import base64
import io
from datetime import date, timedelta
import matplotlib.pyplot as plt

# Configuración para reducir uso de memoria
plt.rcParams.update({
    'figure.max_open_warning': 0,
    'figure.figsize': (10.0, 7.0),  # Tamaño reducido
    'savefig.dpi': 100,  # DPI más bajo
    'savefig.bbox': 'tight',
    'savefig.pad_inches': 0.05,
    'axes.labelsize': 9,
    'axes.titlesize': 10,
    'font.size': 8,
    'legend.fontsize': 8,
})

class FishingZoneLog(models.Model):
    """Bitácora de Actividad en Zona."""
    _name = 'fishing.zone.log'
    _description = 'Bitácora de Actividad en Zona'
    _order = 'date desc'

    zone_id = fields.Many2one('fishing.zone', string='Zona Pesquera', required=True, ondelete='cascade')
    vessel_id = fields.Many2one('fishing.vessel', string='Navío', required=True)
    date = fields.Datetime(string='Fecha y Hora', default=fields.Datetime.now, required=True)
    
    activity_type = fields.Selection([
        ('entry', 'Entrada a Zona'),
        ('exit', 'Salida de Zona'),
        ('capture', 'Reporte de Captura')
    ], string='Tipo de Actividad', required=True)

    species = fields.Selection([
        ('anchovy', 'Anchoa'),
        ('sardine', 'Sardina'),
        ('mackerel', 'Caballa'),
        ('tuna', 'Atún'),
        ('cod', 'Bacalao')
    ], string='Especie Capturada')
    
    catch_kg = fields.Float(string='Captura (Kg)')


class FishingVesselLog(models.Model):
    """Bitácora detallada del navío."""
    _name = 'fishing.vessel.log'
    _description = 'Bitácora del Navío'
    _order = 'log_date desc'
    
    vessel_id = fields.Many2one(
        'fishing.vessel', 
        string='Navío', 
        required=True, 
        ondelete='cascade'
    )
    
    log_date = fields.Datetime(
        string='Fecha y Hora', 
        default=fields.Datetime.now,
        required=True
    )
    
    log_type = fields.Selection([
        ('zone_entry', 'Entrada a Zona'),
        ('zone_exit', 'Salida de Zona'),
        ('capture', 'Reporte de Captura'),
        ('checkpoint', 'Punto de Control'),
        ('status_change', 'Cambio de Estado'),
        ('departure', 'Zarpe'),
        ('arrival', 'Arribo'),
        ('maintenance_start', 'Inicio Mantenimiento'),
        ('maintenance_end', 'Fin Mantenimiento'),
        ('crew_change', 'Cambio de Tripulación'),
        ('fuel_loading', 'Carga de Combustible'),
        ('supply_loading', 'Carga de Provisiones'),
        ('inspection', 'Inspección'),
        ('emergency', 'Emergencia')
    ], string='Tipo de Evento', required=True)
    
    zone_id = fields.Many2one('fishing.zone', string='Zona')
    
    latitude = fields.Float(string='Latitud', digits=(10, 7))
    longitude = fields.Float(string='Longitud', digits=(10, 7))
    
    species = fields.Selection([
        ('anchovy', 'Anchoa'),
        ('sardine', 'Sardina'),
        ('mackerel', 'Caballa'),
        ('tuna', 'Atún'),
        ('cod', 'Bacalao')
    ], string='Especie Capturada')
    
    catch_kg = fields.Float(string='Captura (Kg)')
    
    notes = fields.Text(string='Notas Adicionales')
    
    # Campos calculados optimizados
    zone_name = fields.Char(string='Zona', compute='_compute_zone_name', store=True)
    vessel_name = fields.Char(string='Navío', compute='_compute_vessel_name', store=True)
    vessel_state = fields.Char(string='Estado', compute='_compute_vessel_state', store=True)
    
    @api.depends('zone_id')
    def _compute_zone_name(self):
        for record in self:
            record.zone_name = record.zone_id.name if record.zone_id else ''
    
    @api.depends('vessel_id')
    def _compute_vessel_name(self):
        for record in self:
            if record.vessel_id:
                record.vessel_name = f"{record.vessel_id.name} [{record.vessel_id.license_plate}]"
            else:
                record.vessel_name = ''
    
    @api.depends('vessel_id.state')
    def _compute_vessel_state(self):
        for record in self:
            record.vessel_state = record.vessel_id.state if record.vessel_id else ''


class FishingZone(models.Model):
    """Representa una zona pesquera."""
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
    """Modelo que representa un navío pesquero."""
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

    last_departure_datetime = fields.Datetime(string='Fecha y Hora de Zarpe', tracking=True)
    
    current_zone_id = fields.Many2one(
        'fishing.zone', 
        string='Zona Actual / Destino',
        tracking=True
    )

    current_latitude = fields.Float(string='Latitud Actual', digits=(10, 7))
    current_longitude = fields.Float(string='Longitud Actual', digits=(10, 7))

    vessel_log_ids = fields.One2many(
        'fishing.vessel.log',
        'vessel_id',
        string='Bitácora del Navío',
        readonly=True
    )
    
    image = fields.Image(string="Foto del Navío")
    tripulation_size = fields.Integer(string='Tamaño de la Tripulación')
    
    @api.model
    def create(self, vals):
        """Crear navío y registrar entrada a zona si aplica."""
        record = super(FishingVessel, self).create(vals)
        if record.current_zone_id:
            record._register_zone_change(record.current_zone_id.id, 'entry')
        return record

    def write(self, vals):
        """Registrar cambios de estado y zona en bitácora."""
        # Registrar cambio de estado
        if 'state' in vals:
            old_state = self.state
            new_state = vals['state']
            self._register_status_change(old_state, new_state)
        
        # Registrar cambio de zona
        if 'current_zone_id' in vals:
            old_zone_id = self.current_zone_id.id
            new_zone_id = vals['current_zone_id']
            
            result = super(FishingVessel, self).write(vals)

            if old_zone_id and old_zone_id != new_zone_id:
                self._register_zone_change(old_zone_id, 'exit')
            if new_zone_id and old_zone_id != new_zone_id:
                self._register_zone_change(new_zone_id, 'entry')
                
            return result
        
        return super(FishingVessel, self).write(vals)

    def _register_zone_change(self, zone_id, activity_type):
        """Registrar entrada/salida de zona."""
        for vessel in self:
            # Registrar en fishing.zone.log
            zone_log = self.env['fishing.zone.log'].create({
                'zone_id': zone_id,
                'vessel_id': vessel.id,
                'activity_type': activity_type,
                'date': fields.Datetime.now(),
            })
            
            # Registrar en fishing.vessel.log
            log_type = 'zone_entry' if activity_type == 'entry' else 'zone_exit'
            zone = self.env['fishing.zone'].browse(zone_id)
            self.env['fishing.vessel.log'].create({
                'vessel_id': vessel.id,
                'log_date': fields.Datetime.now(),
                'log_type': log_type,
                'zone_id': zone_id,
                'latitude': vessel.current_latitude,
                'longitude': vessel.current_longitude,
                'notes': f"{'Entrada' if activity_type == 'entry' else 'Salida'} a zona {zone.name}"
            })

    def _register_status_change(self, old_state, new_state):
        """Registrar cambio de estado."""
        for vessel in self:
            self.env['fishing.vessel.log'].create({
                'vessel_id': vessel.id,
                'log_date': fields.Datetime.now(),
                'log_type': 'status_change',
                'latitude': vessel.current_latitude,
                'longitude': vessel.current_longitude,
                'notes': f"Cambio de estado: {old_state} → {new_state}"
            })
    
    @api.onchange('current_zone_id')
    def _onchange_current_zone_id(self):
        """Actualizar coordenadas cuando cambia la zona."""
        if self.current_zone_id:
            self.current_latitude = self.current_zone_id.latitude
            self.current_longitude = self.current_zone_id.longitude
        else:
            self.current_latitude = False
            self.current_longitude = False

    # --- MÉTODOS DE ACCIÓN OPTIMIZADOS ---
    
    def action_register_checkpoint(self):
        """Registrar punto de control."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Registrar Punto de Control',
            'res_model': 'fishing.checkpoint.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_vessel_id': self.id,
                'default_latitude': self.current_latitude,
                'default_longitude': self.current_longitude,
            }
        }
    
    def action_register_departure(self):
        """Registrar zarpe."""
        for vessel in self:
            self.env['fishing.vessel.log'].create({
                'vessel_id': vessel.id,
                'log_date': fields.Datetime.now(),
                'log_type': 'departure',
                'latitude': vessel.current_latitude,
                'longitude': vessel.current_longitude,
                'notes': "Zarpe del navío"
            })
            vessel.write({
                'state': 'fishing',
                'last_departure_datetime': fields.Datetime.now()
            })
        return True
    
    def action_register_arrival(self):
        """Registrar arribo."""
        for vessel in self:
            self.env['fishing.vessel.log'].create({
                'vessel_id': vessel.id,
                'log_date': fields.Datetime.now(),
                'log_type': 'arrival',
                'latitude': vessel.current_latitude,
                'longitude': vessel.current_longitude,
                'notes': "Arribo al muelle"
            })
            vessel.write({'state': 'docked'})
        return True
    
    def action_start_maintenance(self):
        """Iniciar mantenimiento."""
        for vessel in self:
            self.env['fishing.vessel.log'].create({
                'vessel_id': vessel.id,
                'log_date': fields.Datetime.now(),
                'log_type': 'maintenance_start',
                'notes': "Inicio de mantenimiento"
            })
            vessel.write({'state': 'maintenance'})
        return True
    
    def action_end_maintenance(self):
        """Finalizar mantenimiento."""
        for vessel in self:
            self.env['fishing.vessel.log'].create({
                'vessel_id': vessel.id,
                'log_date': fields.Datetime.now(),
                'log_type': 'maintenance_end',
                'notes': "Fin de mantenimiento"
            })
            vessel.write({'state': 'docked'})
        return True
    
    def _get_wizard_action(self, model_name, name):
        """Método genérico para obtener acciones de wizard."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': name,
            'res_model': model_name,
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_vessel_id': self.id},
        }
    
    def action_register_fuel_loading(self):
        return self._get_wizard_action('fishing.fuel.wizard', 'Carga de Combustible')
    
    def action_register_supplies(self):
        return self._get_wizard_action('fishing.supplies.wizard', 'Carga de Provisiones')
    
    def action_register_crew_change(self):
        return self._get_wizard_action('fishing.crew.wizard', 'Cambio de Tripulación')
    
    def action_register_inspection(self):
        return self._get_wizard_action('fishing.inspection.wizard', 'Registrar Inspección')
    
    def action_register_emergency(self):
        return self._get_wizard_action('fishing.emergency.wizard', 'Registrar Emergencia')


class FishingShoal(models.Model):
    """Registro de avistamientos de cardúmenes."""
    _name = 'fishing.shoal'
    _description = 'Registro de Cardumen'

    name = fields.Char(string='Identificador', default='Nuevo')
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
        """Asignar nombre automático."""
        if vals.get('name', 'Nuevo') == 'Nuevo':
            vals['name'] = self.env['ir.sequence'].next_by_code('fishing.shoal') or 'CARDUMEN'
        return super(FishingShoal, self).create(vals)


class FishingCaptureWizard(models.TransientModel):
    """Wizard para reportar capturas."""
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
        readonly=False
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
        """Calcular zona por defecto."""
        for record in self:
            record.current_zone_id = record.vessel_id.current_zone_id
            
    def action_register_capture(self):
        """Registrar captura en ambas bitácoras."""
        self.ensure_one()
        
        if not self.current_zone_id:
            raise exceptions.UserError('Debe especificar una Zona de Reporte.')

        # Registrar en fishing.zone.log
        zone_log = self.env['fishing.zone.log'].create({
            'zone_id': self.current_zone_id.id,
            'vessel_id': self.vessel_id.id,
            'activity_type': 'capture',
            'species': self.species,
            'catch_kg': self.catch_kg,
            'date': fields.Datetime.now(),
        })

        # Registrar en fishing.vessel.log
        species_name = dict(self._fields['species'].selection).get(self.species)
        self.env['fishing.vessel.log'].create({
            'vessel_id': self.vessel_id.id,
            'log_date': fields.Datetime.now(),
            'log_type': 'capture',
            'zone_id': self.current_zone_id.id,
            'species': self.species,
            'catch_kg': self.catch_kg,
            'latitude': self.vessel_id.current_latitude,
            'longitude': self.vessel_id.current_longitude,
            'notes': f"Captura: {self.catch_kg} kg de {species_name}"
        })
        
        return {'type': 'ir.actions.act_window_close'}


# --- WIZARDS SIMPLIFICADOS ---

class FishingCheckpointWizard(models.TransientModel):
    """Wizard para puntos de control."""
    _name = 'fishing.checkpoint.wizard'
    _description = 'Wizard para Puntos de Control'
    
    vessel_id = fields.Many2one('fishing.vessel', string='Navío', required=True,
                               default=lambda self: self.env.context.get('default_vessel_id'))
    
    latitude = fields.Float(string='Latitud', digits=(10, 7), required=True,
                           default=lambda self: self.env.context.get('default_latitude'))
    
    longitude = fields.Float(string='Longitud', digits=(10, 7), required=True,
                            default=lambda self: self.env.context.get('default_longitude'))
    
    notes = fields.Text(string='Notas')
    
    def action_register_checkpoint(self):
        self.ensure_one()
        self.env['fishing.vessel.log'].create({
            'vessel_id': self.vessel_id.id,
            'log_date': fields.Datetime.now(),
            'log_type': 'checkpoint',
            'latitude': self.latitude,
            'longitude': self.longitude,
            'notes': self.notes or "Punto de control registrado"
        })
        return {'type': 'ir.actions.act_window_close'}


class FishingFuelWizard(models.TransientModel):
    """Wizard para carga de combustible."""
    _name = 'fishing.fuel.wizard'
    _description = 'Wizard para Carga de Combustible'
    
    vessel_id = fields.Many2one('fishing.vessel', string='Navío', required=True,
                               default=lambda self: self.env.context.get('default_vessel_id'))
    
    fuel_amount = fields.Float(string='Cantidad (L)', required=True)
    fuel_cost = fields.Float(string='Costo')
    supplier = fields.Char(string='Proveedor')
    notes = fields.Text(string='Notas')
    
    def action_register_fuel(self):
        self.ensure_one()
        self.env['fishing.vessel.log'].create({
            'vessel_id': self.vessel_id.id,
            'log_date': fields.Datetime.now(),
            'log_type': 'fuel_loading',
            'notes': f"Carga de {self.fuel_amount}L. Costo: {self.fuel_cost}. {self.notes}"
        })
        return {'type': 'ir.actions.act_window_close'}


class FishingSuppliesWizard(models.TransientModel):
    """Wizard para carga de provisiones."""
    _name = 'fishing.supplies.wizard'
    _description = 'Wizard para Carga de Provisiones'
    
    vessel_id = fields.Many2one('fishing.vessel', string='Navío', required=True,
                               default=lambda self: self.env.context.get('default_vessel_id'))
    
    supplies_type = fields.Selection([
        ('food', 'Alimentos'),
        ('water', 'Agua'),
        ('ice', 'Hielo'),
        ('fishing_gear', 'Equipo de Pesca'),
        ('safety', 'Equipo de Seguridad'),
        ('medical', 'Suministros Médicos'),
        ('other', 'Otros')
    ], string='Tipo de Provisiones', required=True)
    
    quantity = fields.Float(string='Cantidad', required=True)
    unit = fields.Char(string='Unidad', default='kg')
    notes = fields.Text(string='Notas')
    
    def action_register_supplies(self):
        self.ensure_one()
        supply_type = dict(self._fields['supplies_type'].selection).get(self.supplies_type)
        self.env['fishing.vessel.log'].create({
            'vessel_id': self.vessel_id.id,
            'log_date': fields.Datetime.now(),
            'log_type': 'supply_loading',
            'notes': f"Carga: {self.quantity}{self.unit} de {supply_type}. {self.notes}"
        })
        return {'type': 'ir.actions.act_window_close'}


class FishingCrewWizard(models.TransientModel):
    """Wizard para cambio de tripulación."""
    _name = 'fishing.crew.wizard'
    _description = 'Wizard para Cambio de Tripulación'
    
    vessel_id = fields.Many2one('fishing.vessel', string='Navío', required=True,
                               default=lambda self: self.env.context.get('default_vessel_id'))
    
    change_type = fields.Selection([
        ('boarding', 'Embarque'),
        ('disembarking', 'Desembarque'),
        ('captain_change', 'Cambio de Capitán'),
        ('complete_change', 'Cambio Completo')
    ], string='Tipo de Cambio', required=True)
    
    crew_count = fields.Integer(string='Número de Tripulantes', required=True)
    notes = fields.Text(string='Detalles')
    
    def action_register_crew_change(self):
        self.ensure_one()
        change_type = dict(self._fields['change_type'].selection).get(self.change_type)
        self.env['fishing.vessel.log'].create({
            'vessel_id': self.vessel_id.id,
            'log_date': fields.Datetime.now(),
            'log_type': 'crew_change',
            'notes': f"{change_type} de {self.crew_count} tripulantes. {self.notes}"
        })
        return {'type': 'ir.actions.act_window_close'}


class FishingInspectionWizard(models.TransientModel):
    """Wizard para inspección."""
    _name = 'fishing.inspection.wizard'
    _description = 'Wizard para Inspección'
    
    vessel_id = fields.Many2one('fishing.vessel', string='Navío', required=True,
                               default=lambda self: self.env.context.get('default_vessel_id'))
    
    inspection_type = fields.Selection([
        ('safety', 'Seguridad'),
        ('mechanical', 'Mecánica'),
        ('sanitary', 'Sanitaria'),
        ('regular', 'Regular')
    ], string='Tipo de Inspección', required=True)
    
    inspector = fields.Char(string='Inspector', required=True)
    result = fields.Selection([
        ('approved', 'Aprobado'),
        ('conditional', 'Condicional'),
        ('failed', 'No Aprobado')
    ], string='Resultado', required=True)
    
    notes = fields.Text(string='Notas')
    
    def action_register_inspection(self):
        self.ensure_one()
        inspection_type = dict(self._fields['inspection_type'].selection).get(self.inspection_type)
        result = dict(self._fields['result'].selection).get(self.result)
        self.env['fishing.vessel.log'].create({
            'vessel_id': self.vessel_id.id,
            'log_date': fields.Datetime.now(),
            'log_type': 'inspection',
            'notes': f"Inspección {inspection_type} por {self.inspector}. Resultado: {result}. {self.notes}"
        })
        return {'type': 'ir.actions.act_window_close'}


class FishingEmergencyWizard(models.TransientModel):
    """Wizard para emergencia."""
    _name = 'fishing.emergency.wizard'
    _description = 'Wizard para Emergencia'
    
    vessel_id = fields.Many2one('fishing.vessel', string='Navío', required=True,
                               default=lambda self: self.env.context.get('default_vessel_id'))
    
    emergency_type = fields.Selection([
        ('medical', 'Médica'),
        ('mechanical', 'Mecánica'),
        ('weather', 'Climática'),
        ('security', 'Seguridad'),
        ('other', 'Otra')
    ], string='Tipo de Emergencia', required=True)
    
    severity = fields.Selection([
        ('low', 'Baja'),
        ('medium', 'Media'),
        ('high', 'Alta')
    ], string='Severidad', required=True)
    
    description = fields.Text(string='Descripción', required=True)
    
    def action_register_emergency(self):
        self.ensure_one()
        emergency_type = dict(self._fields['emergency_type'].selection).get(self.emergency_type)
        severity = dict(self._fields['severity'].selection).get(self.severity)
        self.env['fishing.vessel.log'].create({
            'vessel_id': self.vessel_id.id,
            'log_date': fields.Datetime.now(),
            'log_type': 'emergency',
            'notes': f"EMERGENCIA {severity.upper()}: {emergency_type}. {self.description[:100]}..."
        })
        return {'type': 'ir.actions.act_window_close'}

class FishingReportWizard(models.TransientModel):
    _name = 'fishing.report.wizard'
    _description = 'Wizard de Reportes de Pesca'

    date_from = fields.Date(string='Desde', default=fields.Date.context_today)
    date_to = fields.Date(string='Hasta', default=fields.Date.context_today)
    zone_id = fields.Many2one('fishing.zone', string='Zona Específica')
    species = fields.Selection([
        ('tuna', 'Atún'),
        ('sardine', 'Sardina'),
        ('shrimp', 'Camarón'),
        ('other', 'Otros')
    ], string='Especie')
    
    report_type = fields.Selection([
        ('by_species', 'Captura por Especie'),
        ('by_zone', 'Captura por Zona'),
        ('daily_trend', 'Tendencia Diaria')
    ], string='Tipo de Reporte', required=True, default='by_species')

    # Campos de salida
    report_image = fields.Binary(string='Gráfico Generado', attachment=False)
    report_filename = fields.Char(string='Nombre Archivo')
    report_data = fields.Text(string='Datos Resumidos', readonly=True)

    @api.onchange('report_type')
    def _onchange_report_type(self):
        """Limpia los campos de resultado (imagen y datos) al cambiar el tipo de reporte."""
        # Se establece a False para limpiar el campo Binary y Text en la interfaz
        self.report_image = False
        self.report_data = False
        self.report_filename = False
        
    def generate_report(self):
        """Genera el gráfico con Matplotlib y recarga la vista."""
        self.ensure_one()
        
        # 1. Obtener datos
        domain = [
            ('log_date', '>=', self.date_from),
            ('log_date', '<=', self.date_to)
        ]
        if self.zone_id:
            domain.append(('zone_id', '=', self.zone_id.id))
        if self.species:
            domain.append(('species', '=', self.species))
            
        logs = self.env['fishing.vessel.log'].search(domain)
        
        if not logs:
            raise exceptions.UserError("No hay datos de pesca para los criterios seleccionados.")

        # 2. Preparar datos para plotear
        data_map = {}
        
        if self.report_type == 'by_species':
            for log in logs:
                # CORRECCIÓN: Aseguramos que la clave sea un string, incluso si el campo es False.
                # Utilizamos el nombre de visualización si está disponible, o el valor de la selección.
                key = dict(log._fields['species'].selection).get(log.species, 'Sin Especie')
                data_map[key] = data_map.get(key, 0) + log.catch_kg
            xlabel = 'Especie'
            ylabel = 'Captura (Kg)'
            title = 'Captura Total por Especie'
            
        elif self.report_type == 'by_zone':
            for log in logs:
                # CORRECCIÓN: Si zone_id está vacío (False), usamos la cadena 'Sin Zona'.
                # Si existe, usamos su nombre.
                key = log.zone_id.name if log.zone_id else 'Sin Zona' 
                data_map[key] = data_map.get(key, 0) + log.catch_kg
            xlabel = 'Zona'
            ylabel = 'Captura (Kg)'
            title = 'Captura Total por Zona'

        elif self.report_type == 'daily_trend':
            for log in logs:
                # Convertir datetime a date string para agrupar
                key = log.log_date.strftime('%Y-%m-%d')
                data_map[key] = data_map.get(key, 0) + log.catch_kg
            # Ordenar por fecha
            data_map = dict(sorted(data_map.items()))
            xlabel = 'Fecha'
            ylabel = 'Captura (Kg)'
            title = 'Tendencia Diaria de Capturas'
            
        if not data_map:
             raise exceptions.UserError("No se pudieron agrupar datos válidos para el gráfico.")

        # 3. Crear Gráfico con Matplotlib
        fig = plt.figure(figsize=(10, 6))
        ax = fig.add_subplot(111)
        
        etiquetas = list(data_map.keys())
        valores = list(data_map.values())
        
        # Colores personalizados
        colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', '#8c564b']

        if self.report_type in ['by_species', 'by_zone']:
            bars = ax.bar(etiquetas, valores, color=colors[:len(etiquetas)])
            ax.bar_label(bars, fmt='%.0f kg') # Etiqueta encima de las barras
            plt.xticks(rotation=45, ha='right') # Gira etiquetas para que no se superpongan
            
        else: # daily_trend
            ax.plot(etiquetas, valores, marker='o', linestyle='-', color='#1f77b4')
            plt.xticks(rotation=45, ha='right')
            ax.grid(True, linestyle='--', alpha=0.7)

        ax.set_xlabel(xlabel)
        ax.set_ylabel(ylabel)
        ax.set_title(title)
        
        # Ajustar layout para que no se corten las etiquetas
        plt.tight_layout()

        # 4. Guardar en Buffer de Memoria
        buf = io.BytesIO()
        plt.savefig(buf, format='png', dpi=100)
        buf.seek(0)
        image_content = buf.getvalue()
        buf.close()
        
        # Limpiar matplotlib para liberar memoria
        plt.close('all')

        # 5. Escribir en la base de datos
        self.write({
            'report_image': base64.b64encode(image_content),
            'report_filename': f'reporte_{self.report_type}.png',
            'report_data': f"Datos procesados: {len(logs)} registros. Total Kg: {sum(valores)}"
        })

        # 6. RETORNAR ACCIÓN PARA REFRESCAR LA VISTA
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'fishing.report.wizard',
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }

    def action_download_report(self):
        """Permite descargar la imagen generada."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content?model=fishing.report.wizard&id={self.id}&field=report_image&download=true&filename={self.report_filename}',
            'target': 'self',
        }
    
    def action_test_chart(self):
        """Genera un gráfico de prueba simple sin leer la BD."""
        fig = plt.figure(figsize=(6, 4))
        plt.plot([1, 2, 3, 4], [10, 20, 25, 30], label='Prueba')
        plt.title("Gráfico de Prueba")
        plt.legend()
        
        buf = io.BytesIO()
        plt.savefig(buf, format='png')
        buf.seek(0)
        content = buf.getvalue()
        buf.close()
        plt.close('all')
        
        self.write({
            'report_image': base64.b64encode(content),
            'report_filename': 'test.png',
            'report_data': 'Gráfico de prueba generado.'
        })
        
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'fishing.report.wizard',
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }