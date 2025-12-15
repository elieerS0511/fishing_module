# SECCIÓN 1: CONFIGURACIÓN INICIAL E IMPORTS
# Importar matplotlib ANTES de cualquier otro import relacionado con gráficos
# 'Agg' es un backend que NO requiere interfaz gráfica (GUI)
# Esencial para servidores headless (sin pantalla) como Odoo
import matplotlib
matplotlib.use('Agg')  # DEBE ESTAR ANTES de importar plt
# Importaciones estándar de Odoo
from odoo import models, fields, api, exceptions
# Importaciones para manejo de archivos y codificación
import base64    # Para codificar/decodificar archivos binarios (imágenes)
import io        # Para trabajar con buffers de memoria (BytesIO)
# Importaciones para manejo de fechas
from datetime import date, timedelta
# Importar matplotlib.pyplot para crear gráficos
# DEBE importarse DESPUÉS de configurar matplotlib.use('Agg')
import matplotlib.pyplot as plt

# SECCIÓN 2: CONFIGURACIÓN DE MATPLOTLIB PARA OPTIMIZACIÓN
"""
CONFIGURACIÓN DE RCPARAMS (RUNTIME CONFIGURATION PARAMETERS)
Estos ajustes optimizan matplotlib para uso en servidor Odoo:
1. Reduce uso de memoria
2. Mejora rendimiento
3. Ajusta tamaño y calidad de imágenes
4. Optimiza para generación en batch
"""
# Actualizar parámetros de configuración de matplotlib
plt.rcParams.update({
    # Desactivar advertencias por muchas figuras abiertas
    # Útil cuando se generan múltiples reportes
    'figure.max_open_warning': 0, 
    # Tamaño por defecto de las figuras (ancho, alto en pulgadas)
    # 10x7 pulgadas es un buen balance entre tamaño y legibilidad
    'figure.figsize': (10.0, 7.0),
    # DPI (Dots Per Inch) al guardar imágenes
    # 100 DPI es suficiente para visualización web, reduce tamaño de archivo
    'savefig.dpi': 100,
    # Recortar espacios en blanco alrededor de la figura al guardar
    'savefig.bbox': 'tight',
    # Padding interno al guardar (en pulgadas)
    # Reducido a 0.05 para minimizar espacio desperdiciado
    'savefig.pad_inches': 0.05,
    # Tamaño de fuente para etiquetas de ejes
    'axes.labelsize': 9,
    # Tamaño de fuente para títulos
    'axes.titlesize': 10,
    # Tamaño de fuente general
    'font.size': 8,
    # Tamaño de fuente para leyendas
    'legend.fontsize': 8,
})

# SECCIÓN 3: MODELO FishingZoneLog - BITÁCORA POR ZONA
class FishingZoneLog(models.Model):
    """
    MODELO: FishingZoneLog - Bitácora de Actividad en Zona Pesquera
    PROPÓSITO:
    Registra todas las actividades que ocurren en cada zona pesquera:
    - Entrada de navíos a la zona
    - Salida de navíos de la zona
    - Capturas realizadas en la zona
    RELACIONES:
    - Muchos a Uno (Many2one) con FishingZone: Cada registro pertenece a una zona
    - Muchos a Uno (Many2one) con FishingVessel: Cada registro es realizado por un navío
    """
    # Nombre técnico del modelo (usado en la base de datos)
    _name = 'fishing.zone.log'
    # Descripción legible para humanos
    _description = 'Bitácora de Actividad en Zona'
    # Orden por defecto: registros más recientes primero
    _order = 'date desc'

    # CAMPOS (COLUMNAS DE LA BASE DE DATOS)
    # Zona donde ocurrió la actividad (relación obligatoria)
    # ondelete='cascade': Si se elimina la zona, se eliminan sus registros
    zone_id = fields.Many2one(
        'fishing.zone', 
        string='Zona Pesquera', 
        required=True, 
        ondelete='cascade'
    )
    # Navío que realizó la actividad (relación obligatoria)
    vessel_id = fields.Many2one(
        'fishing.vessel', 
        string='Navío', 
        required=True
    )
    # Fecha y hora de la actividad
    # default=fields.Datetime.now: Fecha/hora actual automáticamente
    date = fields.Datetime(
        string='Fecha y Hora', 
        default=fields.Datetime.now, 
        required=True
    )
    # Tipo de actividad realizada en la zona
    # Selection: Lista de valores predefinidos
    activity_type = fields.Selection(
        selection=[
            ('entry', 'Entrada a Zona'),
            ('exit', 'Salida de Zona'),
            ('capture', 'Reporte de Captura')
        ], 
        string='Tipo de Actividad', 
        required=True
    )
    # Especie de pez capturada (solo aplica para actividades de captura)
    # Selection: Especies comunes en pesca
    species = fields.Selection(
        selection=[
            ('anchovy', 'Anchoa'),
            ('sardine', 'Sardina'),
            ('mackerel', 'Caballa'),
            ('tuna', 'Atún'),
            ('cod', 'Bacalao')
        ], 
        string='Especie Capturada'
    )
    # Cantidad capturada en kilogramos (solo para actividades de captura)
    catch_kg = fields.Float(string='Captura (Kg)')

# SECCIÓN 4: MODELO FishingVesselLog - BITÁCORA POR NAVÍO
class FishingVesselLog(models.Model):
    """
    MODELO: FishingVesselLog - Bitácora Detallada del Navío
    PROPÓSITO:
    Registra TODOS los eventos importantes de un navío pesquero:
    - Cambios de estado (muelle → pesca → mantenimiento)
    - Entradas y salidas de zonas
    - Capturas de pesca
    - Puntos de control GPS
    - Operaciones administrativas (combustible, provisiones, etc.)
    - Emergencias e inspecciones
    CARACTERÍSTICAS:
    - Campos calculados optimizados (almacenados para mejor rendimiento)
    - Ordenado por fecha descendente (eventos más recientes primero)
    - Relación en cascada: si se elimina el navío, se eliminan sus registros
    """
    # Nombre técnico del modelo
    _name = 'fishing.vessel.log'
    # Descripción legible
    _description = 'Bitácora del Navío'
    # Orden por defecto: eventos más recientes primero
    _order = 'log_date desc'
    # CAMPOS DE RELACIÓN
    # Navío al que pertenece este registro de bitácora
    # ondelete='cascade': Eliminar registros si se elimina el navío
    vessel_id = fields.Many2one(
        'fishing.vessel', 
        string='Navío', 
        required=True, 
        ondelete='cascade'
    )
    
    # CAMPOS DE FECHA Y TIPO
    # Fecha y hora exacta del evento
    log_date = fields.Datetime(
        string='Fecha y Hora', 
        default=fields.Datetime.now,
        required=True
    )
    # Tipo de evento (lista completa de posibles eventos del navío)
    log_type = fields.Selection(
        selection=[
            # Eventos de ubicación/zona
            ('zone_entry', 'Entrada a Zona'),
            ('zone_exit', 'Salida de Zona'),
            ('capture', 'Reporte de Captura'),
            ('checkpoint', 'Punto de Control'),       
            # Eventos de estado del navío
            ('status_change', 'Cambio de Estado'),
            ('departure', 'Zarpe'),
            ('arrival', 'Arribo'),
            ('maintenance_start', 'Inicio Mantenimiento'),
            ('maintenance_end', 'Fin Mantenimiento'),
            # Eventos administrativos
            ('crew_change', 'Cambio de Tripulación'),
            ('fuel_loading', 'Carga de Combustible'),
            ('supply_loading', 'Carga de Provisiones'),
            ('inspection', 'Inspección'),
            ('emergency', 'Emergencia')
        ], 
        string='Tipo de Evento', 
        required=True
    )
    
    # CAMPOS DE UBICACIÓN
    # Zona relacionada con el evento (opcional, algunos eventos no tienen zona)
    zone_id = fields.Many2one('fishing.zone', string='Zona')
    # Coordenadas GPS del evento
    # digits=(10, 7): 10 dígitos totales, 7 decimales (≈1.1 cm precisión)
    latitude = fields.Float(string='Latitud', digits=(10, 7))
    longitude = fields.Float(string='Longitud', digits=(10, 7))
    # CAMPOS DE CAPTURA (PARA EVENTOS DE CAPTURA)
    # Especie capturada (solo para eventos de tipo 'capture')
    species = fields.Selection(
        selection=[
            ('anchovy', 'Anchoa'),
            ('sardine', 'Sardina'),
            ('mackerel', 'Caballa'),
            ('tuna', 'Atún'),
            ('cod', 'Bacalao')
        ], 
        string='Especie Capturada'
    )
    # Cantidad capturada en kilogramos
    catch_kg = fields.Float(string='Captura (Kg)')
    
    # CAMPOS DE TEXTO LIBRE
    # Notas adicionales sobre el evento
    # Text: Campo de texto largo sin límite específico
    notes = fields.Text(string='Notas Adicionales')
    
    # CAMPOS CALCULADOS OPTIMIZADOS (STORED)
    # Estos campos se calculan automáticamente pero se almacenan en la BD
    # para mejor rendimiento en búsquedas y filtros
    # Nombre de la zona (calculado a partir de zone_id.name)
    # store=True: Se almacena en BD, no se calcula en tiempo real
    zone_name = fields.Char(
        string='Zona', 
        compute='_compute_zone_name', 
        store=True
    )
    # Nombre del navío con formato: "Nombre [Matrícula]"
    vessel_name = fields.Char(
        string='Navío', 
        compute='_compute_vessel_name', 
        store=True
    )
    # Estado del navío en el momento del evento
    vessel_state = fields.Char(
        string='Estado', 
        compute='_compute_vessel_state', 
        store=True
    )
    
    # MÉTODOS COMPUTE (CÁLCULO DE CAMPOS)
    @api.depends('zone_id')
    def _compute_zone_name(self):
        """
        CALCULA EL NOMBRE DE LA ZONA
        Método decorado con @api.depends: Se ejecuta cuando cambia zone_id
    Propósito:
        - Obtiene el nombre legible de la zona relacionada
        - Si no hay zona, retorna cadena vacía
        - Mejora rendimiento almacenando en BD en lugar de calcular en vista
        """
        for record in self:
            # Si existe relación con zona, obtener su nombre
            # Si no existe (zone_id es False), asignar cadena vacía
            record.zone_name = record.zone_id.name if record.zone_id else ''
    @api.depends('vessel_id')
    def _compute_vessel_name(self):
        """
        CALCULA EL NOMBRE DEL NAVÍO CON MATRÍCULA
        Formato: "Nombre del Navío [Matrícula]"
        Ejemplo: "Pescador IV [ABC-123]"
        """
        for record in self:
            if record.vessel_id:
                # Formatear: Nombre + espacio + [Matrícula]
                record.vessel_name = f"{record.vessel_id.name} [{record.vessel_id.license_plate}]"
            else:
                # Si no hay navío, cadena vacía
                record.vessel_name = ''
    @api.depends('vessel_id.state')
    def _compute_vessel_state(self):
        """
        CALCULA EL ESTADO DEL NAVÍO
        Obtiene el estado actual del navío relacionado
        """
        for record in self:
            # Si existe navío, obtener su estado, sino cadena vacía
            record.vessel_state = record.vessel_id.state if record.vessel_id else ''
# SECCIÓN 5: MODELO FishingZone - ZONAS PESQUERAS
class FishingZone(models.Model):
    """
    MODELO: FishingZone - Zonas Pesqueras
    PROPÓSITO:
    Define áreas geográficas donde se permite o se realiza la pesca.
    Cada zona tiene coordenadas centrales, tipo y registros de actividad.
    RELACIONES:
    - One2many con FishingVessel: Navíos actualmente en esta zona
    - One2many con FishingZoneLog: Historial de actividad en esta zona.
    """
    _name = 'fishing.zone'
    _description = 'Zona Pesquera'
    # CAMPOS DE IDENTIFICACIÓN
    # Nombre descriptivo de la zona (ej: "Banco de Pesca Norte")
    name = fields.Char(string='Nombre de la Zona', required=True)
    # Código único para identificación rápida (ej: "Z-001", "BPN-2023")
    code = fields.Char(string='Código de Zona')
    # CAMPOS GEOGRÁFICOS
    # Coordenadas del punto central de la zona
    latitude = fields.Float(string='Latitud Centro', digits=(10, 7))
    longitude = fields.Float(string='Longitud Centro', digits=(10, 7))
    # CAMPOS DE CLASIFICACIÓN
    # Tipo de zona (afecta regulaciones y permisos)
    zone_type = fields.Selection(
        selection=[
            ('coast', 'Costera'),
            ('deep_sea', 'Alta Mar'),
            ('restricted', 'Restringida')
        ], 
        string='Tipo de Zona', 
        required=True
    )
    # Campo activo para desactivar zonas sin eliminarlas
    active = fields.Boolean(default=True)
    # RELACIONES CON OTROS MODELOS
    # Navíos que están actualmente en esta zona
    # current_zone_id es el campo inverso en FishingVessel
    vessel_ids = fields.One2many(
        'fishing.vessel', 
        'current_zone_id', 
        string='Navíos en la Zona'
    )
    # Historial de actividades registradas en esta zona
    log_ids = fields.One2many(
        'fishing.zone.log', 
        'zone_id', 
        string='Bitácora de Actividades'
    )
# SECCIÓN 6: MODELO FishingVessel - NAVÍOS PESQUEROS (MODELO PRINCIPAL)
class FishingVessel(models.Model):
    """
    MODELO: FishingVessel - Navío Pesquero (MODELO PRINCIPAL)
    PROPÓSITO:
    Representa un navío pesquero y gestiona TODO su ciclo de vida:
    - Información básica (nombre, matrícula, capacidad)
    - Estado actual (muelle, pesca, mantenimiento)
    - Ubicación GPS y zona actual
    - Historial completo de actividades (bitácora)
    - Operaciones administrativas
    
    HERENCIA:
    - mail.thread: Sistema de mensajería y seguimiento de Odoo
    - mail.activity.mixin: Permite crear actividades/recordatorios
    
    ESTADOS (STATE):
    1. 'docked': En Muelle - Listo para zarpar o en mantenimiento
    2. 'fishing': En Faena - Actualmente pescando
    3. 'maintenance': Mantenimiento - En reparación o mantenimiento
    
    FLUJO DE ESTADOS:
    docked → fishing (al zarpar)
    fishing → docked (al arribar)
    docked → maintenance (al iniciar mantenimiento)
    maintenance → docked (al finalizar mantenimiento)
    """
    # Nombre técnico del modelo
    _name = 'fishing.vessel'
    # Descripción legible
    _description = 'Navío Pesquero'
    # Heredar funcionalidad de mensajería y actividades de Odoo
    _inherit = ['mail.thread', 'mail.activity.mixin']
    # CAMPOS DE INFORMACIÓN BÁSICA
    # Nombre identificativo del navío (ej: "Pescador IV", "Mar Azul")
    # tracking=True: Registra cambios para auditoría
    name = fields.Char(string='Nombre del Navío', required=True, tracking=True)
    # Matrícula o placa oficial del navío
    license_plate = fields.Char(string='Matrícula', required=True)
    # Capitán a cargo (relación con contacto/res.partner)
    captain_id = fields.Many2one('res.partner', string='Capitán')
    # Capacidad máxima de carga en kilogramos
    capacity_kg = fields.Float(string='Capacidad de Bodega (Kg)')
    # CAMPOS DE ESTADO Y UBICACIÓN
    # Estado actual del navío (controla qué operaciones están disponibles)
    state = fields.Selection(
        selection=[
            ('docked', 'En Muelle'),
            ('fishing', 'En Faena'),
            ('maintenance', 'Mantenimiento')
        ], 
        string='Estado', 
        default='docked',  # Valor por defecto al crear nuevo navío
        tracking=True  # Registrar cambios para auditoría
    )
    # Fecha y hora del último zarpe (cuándo salió del muelle)
    last_departure_datetime = fields.Datetime(
        string='Fecha y Hora de Zarpe', 
        tracking=True
    )
    # Zona actual donde se encuentra el navío
    current_zone_id = fields.Many2one(
        'fishing.zone', 
        string='Zona Actual / Destino',
        tracking=True
    )
    # Coordenadas GPS actuales del navío
    current_latitude = fields.Float(string='Latitud Actual', digits=(10, 7))
    current_longitude = fields.Float(string='Longitud Actual', digits=(10, 7))
    # RELACIONES Y CAMPOS ADICIONALES
    # Todos los registros de bitácora de este navío
    vessel_log_ids = fields.One2many(
        'fishing.vessel.log',
        'vessel_id',
        string='Bitácora del Navío',
        readonly=True  # Solo lectura, se modifica a través de métodos
    )
    # Imagen/foto del navío
    image = fields.Image(string="Foto del Navío")
    # Número de tripulantes a bordo
    tripulation_size = fields.Integer(string='Tamaño de la Tripulación')
    # MÉTODOS DEL CICLO DE VIDA (OVERRIDES)
    @api.model
    def create(self, vals):
        """
        SOBRESCRIBIR MÉTODO CREATE
        Se ejecuta cuando se crea un nuevo registro (navío)
        Comportamiento adicional:
        - Si el nuevo navío tiene una zona actual asignada,
          registra automáticamente una entrada en la bitácora de esa zona
        """
        # Llamar al método create original de Odoo
        record = super(FishingVessel, self).create(vals)
        # Si el navío creado tiene una zona actual
        if record.current_zone_id:
            # Registrar entrada automática a esa zona
            record._register_zone_change(record.current_zone_id.id, 'entry')
        return record
    def write(self, vals):
        """
        SOBRESCRIBIR MÉTODO WRITE
        Se ejecuta cuando se modifican registros existentes
        Detecta cambios específicos y ejecuta acciones adicionales:
        1. Cambios de estado → Registrar en bitácora
        2. Cambios de zona → Registrar entrada/salida en bitácoras
        Args:
            vals (dict): Valores que se están escribiendo
        """
        
        # 1. DETECTAR Y REGISTRAR CAMBIO DE ESTADO
        if 'state' in vals:
            # Guardar estado antiguo antes de cambiarlo
            old_state = self.state
            # Nuevo estado que se va a asignar
            new_state = vals['state']
            # Registrar el cambio de estado en bitácora
            self._register_status_change(old_state, new_state)
        # 2. DETECTAR Y REGISTRAR CAMBIO DE ZONA
        if 'current_zone_id' in vals:
            # Guardar ID de zona antigua
            old_zone_id = self.current_zone_id.id
            # Nuevo ID de zona que se va a asignar
            new_zone_id = vals['current_zone_id']
            # Primero escribir los valores (incluyendo la nueva zona)
            # Esto asegura que current_zone_id esté actualizado para los registros
            result = super(FishingVessel, self).write(vals)
            # Registrar salida de la zona anterior (si existía y es diferente)
            if old_zone_id and old_zone_id != new_zone_id:
                self._register_zone_change(old_zone_id, 'exit')
            # Registrar entrada a la nueva zona (si es diferente)
            if new_zone_id and old_zone_id != new_zone_id:
                self._register_zone_change(new_zone_id, 'entry')
            return result

        # 3. PARA OTROS CAMBIOS, EJECUTAR WRITE NORMAL

        return super(FishingVessel, self).write(vals)
    # MÉTODOS INTERNOS PARA REGISTRO DE ACTIVIDADES
    
    def _register_zone_change(self, zone_id, activity_type):
        """
        REGISTRAR ENTRADA O SALIDA DE ZONA EN AMBAS BITÁCORAS
        Este método se llama cuando un navío entra o sale de una zona.
        Crea registros en:
        1. FishingZoneLog: Actividad por zona (para análisis por zona)
        2. FishingVesselLog: Historial del navío (para seguimiento del navío)
        Args:
            zone_id (int): ID de la zona
            activity_type (str): 'entry' para entrada, 'exit' para salida
        """
        for vessel in self:
            # 1. REGISTRAR EN FISHING.ZONE.LOG (BITÁCORA POR ZONA)
            zone_log = self.env['fishing.zone.log'].create({
                'zone_id': zone_id,
                'vessel_id': vessel.id,
                'activity_type': activity_type,
                'date': fields.Datetime.now(),
            })
            # 2. REGISTRAR EN FISHING.VESSEL.LOG (BITÁCORA DEL NAVÍO)
            # Determinar tipo de log basado en activity_type
            log_type = 'zone_entry' if activity_type == 'entry' else 'zone_exit'
            # Obtener objeto de zona para incluir su nombre en las notas
            zone = self.env['fishing.zone'].browse(zone_id)
            # Crear registro en la bitácora del navío
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
        """
        REGISTRAR CAMBIO DE ESTADO EN BITÁCORA
        Crea un registro en la bitácora del navío cuando cambia su estado.
        Ejemplo: "Cambio de estado: docked → fishing"
        Args:
            old_state (str): Estado anterior
            new_state (str): Estado nuevo
        """
        for vessel in self:
            self.env['fishing.vessel.log'].create({
                'vessel_id': vessel.id,
                'log_date': fields.Datetime.now(),
                'log_type': 'status_change',
                'latitude': vessel.current_latitude,
                'longitude': vessel.current_longitude,
                'notes': f"Cambio de estado: {old_state} → {new_state}"
            })
    
    # MÉTODOS ONCHANGE (REACCIÓN A CAMBIOS EN CAMPOS)
    @api.onchange('current_zone_id')
    def _onchange_current_zone_id(self):
        """
        REACCIONAR AL CAMBIO DE ZONA ACTUAL
        Cuando el usuario selecciona una zona en la interfaz:
        - Actualiza automáticamente las coordenadas del navío
          a las coordenadas centrales de la zona seleccionada
        Esto simplifica la entrada de datos: al seleccionar zona,
        las coordenadas se llenan automáticamente.
        """
        if self.current_zone_id:
            # Si se seleccionó una zona, copiar sus coordenadas
            self.current_latitude = self.current_zone_id.latitude
            self.current_longitude = self.current_zone_id.longitude
        else:
            # Si se deseleccionó (zona vacía), limpiar coordenadas
            self.current_latitude = False
            self.current_longitude = False

    # MÉTODOS DE ACCIÓN (LLAMADOS DESDE BOTONES EN LA INTERFAZ)
    def action_register_checkpoint(self):
        """
        ACCIÓN: REGISTRAR PUNTO DE CONTROL
        Abre un wizard (ventana emergente) para registrar
        la posición GPS actual como un punto de control.
        Returns:
            dict: Acción de Odoo para abrir el wizard
        """
        # Asegurar que solo se opera sobre un registro (no múltiples)
        self.ensure_one()
        # Retornar acción para abrir wizard
        return {
            'type': 'ir.actions.act_window',  # Tipo: abrir ventana
            'name': 'Registrar Punto de Control',  # Título de la ventana
            'res_model': 'fishing.checkpoint.wizard',  # Modelo del wizard
            'view_mode': 'form',  # Solo vista de formulario
            'target': 'new',  # Abrir en ventana emergente
            # Contexto: Valores por defecto para el wizard
            'context': {
                'default_vessel_id': self.id,  # Navío actual
                'default_latitude': self.current_latitude,  # Latitud actual
                'default_longitude': self.current_longitude,  # Longitud actual
            }
        }
    def action_register_departure(self):
        """
        ACCIÓN: REGISTRAR ZARPE (SALIR DEL MUELLE)
        Cambia el estado del navío a 'fishing' (en faena) y:
        1. Registra el evento en la bitácora
        2. Actualiza la fecha/hora del último zarpe
        
        Este método se llama desde el botón "Zarpe" en la interfaz.
        """
        for vessel in self:
            # Registrar evento en bitácora
            self.env['fishing.vessel.log'].create({
                'vessel_id': vessel.id,
                'log_date': fields.Datetime.now(),
                'log_type': 'departure',
                'latitude': vessel.current_latitude,
                'longitude': vessel.current_longitude,
                'notes': "Zarpe del navío"
            })
            # Actualizar estado y fecha de zarpe
            vessel.write({
                'state': 'fishing',  # Cambiar a "en faena"
                'last_departure_datetime': fields.Datetime.now()  # Registrar momento del zarpe
            })
        return True
    def action_register_arrival(self):
        """
        ACCIÓN: REGISTRAR ARRIBO (VOLVER AL MUELLE)
        Cambia el estado del navío a 'docked' (en muelle) y
        registra el evento en la bitácora.
        """
        for vessel in self:
            # Registrar evento en bitácora
            self.env['fishing.vessel.log'].create({
                'vessel_id': vessel.id,
                'log_date': fields.Datetime.now(),
                'log_type': 'arrival',
                'latitude': vessel.current_latitude,
                'longitude': vessel.current_longitude,
                'notes': "Arribo al muelle"
            })
            
            # Cambiar estado a "en muelle"
            vessel.write({'state': 'docked'})
        return True
    
    def action_start_maintenance(self):
        """
        ACCIÓN: INICIAR MANTENIMIENTO
        Cambia el estado del navío a 'maintenance' y
        registra el inicio de mantenimiento en bitácora.
        Solo disponible cuando el navío está en muelle (state='docked').
        """
        for vessel in self:
            # Registrar inicio de mantenimiento
            self.env['fishing.vessel.log'].create({
                'vessel_id': vessel.id,
                'log_date': fields.Datetime.now(),
                'log_type': 'maintenance_start',
                'notes': "Inicio de mantenimiento"
            })
            # Cambiar estado a "mantenimiento"
            vessel.write({'state': 'maintenance'})
        return True
    def action_end_maintenance(self):
        """
        ACCIÓN: FINALIZAR MANTENIMIENTO
        Cambia el estado del navío a 'docked' y
        registra el fin de mantenimiento en bitácora.
        Solo disponible cuando el navío está en mantenimiento.
        """
        for vessel in self:
            # Registrar fin de mantenimiento
            self.env['fishing.vessel.log'].create({
                'vessel_id': vessel.id,
                'log_date': fields.Datetime.now(),
                'log_type': 'maintenance_end',
                'notes': "Fin de mantenimiento"
            })
            # Volver a estado "en muelle"
            vessel.write({'state': 'docked'})
        return True

    # MÉTODO GENÉRICO PARA WIZARDS
    def _get_wizard_action(self, model_name, name):
        """
        MÉTODO GENÉRICO PARA OBTENER ACCIONES DE WIZARD
        Crea la estructura estándar para abrir cualquier wizard.
        Centraliza la lógica común para evitar código repetitivo.
        Args:
            model_name (str): Nombre del modelo del wizard
            name (str): Nombre que se mostrará en la ventana
        Returns:
            dict: Acción de Odoo estándar para abrir wizard
        """
        self.ensure_one()  # Solo funciona con un registro a la vez
        return {
            'type': 'ir.actions.act_window',
            'name': name,
            'res_model': model_name,
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_vessel_id': self.id},
        }

    # MÉTODOS ESPECÍFICOS QUE USAN EL MÉTODO GENÉRICO
    def action_register_fuel_loading(self):
        """Abrir wizard para carga de combustible."""
        return self._get_wizard_action('fishing.fuel.wizard', 'Carga de Combustible')
    def action_register_supplies(self):
        """Abrir wizard para carga de provisiones."""
        return self._get_wizard_action('fishing.supplies.wizard', 'Carga de Provisiones')
    def action_register_crew_change(self):
        """Abrir wizard para cambio de tripulación."""
        return self._get_wizard_action('fishing.crew.wizard', 'Cambio de Tripulación')
    def action_register_inspection(self):
        """Abrir wizard para registrar inspección."""
        return self._get_wizard_action('fishing.inspection.wizard', 'Registrar Inspección')
    def action_register_emergency(self):
        """Abrir wizard para registrar emergencia."""
        return self._get_wizard_action('fishing.emergency.wizard', 'Registrar Emergencia')
       
# SECCIÓN 7: MODELO FishingShoal - REGISTRO DE CARDÚMENES
class FishingShoal(models.Model):
    """
    MODELO: FishingShoal - Registro de Avistamientos de Cardúmenes    
    """
    _name = 'fishing.shoal'
    _description = 'Registro de Cardumen'
    # CAMPOS DE IDENTIFICACIÓN
    # Identificador único, generado automáticamente por secuencia
    name = fields.Char(string='Identificador', default='Nuevo')
    # CAMPOS DEL CARDUMEN
    # Especie del cardumen avistado
    species = fields.Selection(
        selection=[
            ('anchovy', 'Anchoa'),
            ('sardine', 'Sardina'),
            ('mackerel', 'Caballa'),
            ('tuna', 'Atún'),
            ('cod', 'Bacalao')
        ], 
        string='Especie', 
        required=True
    )
    # Estimación del tamaño del cardumen en toneladas
    estimated_tonnage = fields.Float(string='Tonelaje Estimado')
    # Fecha y hora del avistamiento
    observation_date = fields.Datetime(
        string='Fecha de Avistamiento', 
        default=fields.Datetime.now
    )
    # CAMPOS DE UBICACIÓN Y RELACIONES
    # Zona donde se avistó el cardumen
    zone_id = fields.Many2one('fishing.zone', string='Zona de Avistamiento')
    # Navío que realizó el avistamiento
    spotted_by_vessel_id = fields.Many2one(
        'fishing.vessel', 
        string='Avistado por Navío'
    )
    # CAMPOS DE TEXTO LIBRE
    # Notas sobre condiciones oceanográficas en el momento del avistamiento
    notes = fields.Text(string='Notas Oceanográficas')
    # MÉTODO CREATE PARA ASIGNAR NOMBRE AUTOMÁTICO
    
    @api.model
    def create(self, vals):
        """
        SOBRESCRIBIR MÉTODO CREATE PARA ASIGNAR NOMBRE AUTOMÁTICO
        Si no se proporciona un nombre, genera uno automáticamente
        usando una secuencia de Odoo.
        La secuencia debe estar definida en el módulo con código 'fishing.shoal'
        """
        # Si no se proporciona nombre o es 'Nuevo' (valor por defecto)
        if vals.get('name', 'Nuevo') == 'Nuevo':
            # Obtener próximo valor de la secuencia 'fishing.shoal'
            vals['name'] = self.env['ir.sequence'].next_by_code('fishing.shoal') or 'CARDUMEN'
        # Llamar al método create original con los valores actualizados
        return super(FishingShoal, self).create(vals)
# SECCIÓN 8: WIZARD FishingCaptureWizard - REPORTAR CAPTURAS
class FishingCaptureWizard(models.TransientModel):
    """
    WIZARD: FishingCaptureWizard - Reportar Capturas de Pesca    
    NOTAS:
    - Modelo TransientModel: Los registros se eliminan automáticamente después de un tiempo
    - No se almacena permanentemente, solo para capturar datos temporalmente
    """
    _name = 'fishing.capture.wizard'
    _description = 'Wizard para Reportar Captura'
    # CAMPOS DEL WIZARD
    # Navío que realiza la captura (obligatorio)
    vessel_id = fields.Many2one(
        'fishing.vessel', 
        string='Navío', 
        required=True, 
        # Valor por defecto: ID del registro activo (navío desde donde se abrió)
        default=lambda self: self.env.context.get('active_id')
    )
    # Zona donde se realiza la captura
    current_zone_id = fields.Many2one(
        'fishing.zone', 
        string='Zona de Reporte',
        required=True,
        # Campo calculado pero editable (compute con store=True y readonly=False)
        compute='_compute_zone',
        store=True,
        readonly=False
    )
    # Especie capturada (selección obligatoria)
    species = fields.Selection(
        selection=[
            ('anchovy', 'Anchoa'),
            ('sardine', 'Sardina'),
            ('mackerel', 'Caballa'),
            ('tuna', 'Atún'),
            ('cod', 'Bacalao')
        ], 
        string='Especie Capturada', 
        required=True
    )
    # Cantidad capturada en kilogramos (obligatorio)
    catch_kg = fields.Float(string='Captura (Kg)', required=True)
    # MÉTODOS COMPUTE
    @api.depends('vessel_id')
    def _compute_zone(self):
        """
        CALCULAR ZONA POR DEFECTO
        Sugiere automáticamente la zona actual del navío como zona de reporte.
        El usuario puede cambiarla si es necesario.
        """
        for record in self:
            # Asignar la zona actual del navío como valor por defecto
            record.current_zone_id = record.vessel_id.current_zone_id
            
    # MÉTODOS DE ACCIÓN
    def action_register_capture(self):
        """
        ACCIÓN: REGISTRAR CAPTURA EN AMBAS BITÁCORAS
        
        Este método se ejecuta al hacer clic en "Registrar Bitácora".        
        Raises:
            exceptions.UserError: Si no se especifica zona de reporte
        """
        # Asegurar que solo se procesa un registro (aunque el wizard siempre es uno)
        self.ensure_one()
           # Validar que se haya especificado una zona
        if not self.current_zone_id:
            raise exceptions.UserError('Debe especificar una Zona de Reporte.')
        # 1. REGISTRAR EN FISHING.ZONE.LOG (BITÁCORA POR ZONA)
        zone_log = self.env['fishing.zone.log'].create({
            'zone_id': self.current_zone_id.id,
            'vessel_id': self.vessel_id.id,
            'activity_type': 'capture',  # Tipo: reporte de captura
            'species': self.species,
            'catch_kg': self.catch_kg,
            'date': fields.Datetime.now(),
        })

        # 2. REGISTRAR EN FISHING.VESSEL.LOG (BITÁCORA DEL NAVÍO)
        # Obtener nombre legible de la especie
        species_name = dict(self._fields['species'].selection).get(self.species)
        # Crear registro en la bitácora del navío
        self.env['fishing.vessel.log'].create({
            'vessel_id': self.vessel_id.id,
            'log_date': fields.Datetime.now(),
            'log_type': 'capture',  # Tipo: captura
            'zone_id': self.current_zone_id.id,
            'species': self.species,
            'catch_kg': self.catch_kg,
            'latitude': self.vessel_id.current_latitude,
            'longitude': self.vessel_id.current_longitude,
            'notes': f"Captura: {self.catch_kg} kg de {species_name}"
        })
        # Retornar acción para cerrar el wizard
        return {'type': 'ir.actions.act_window_close'}
# SECCIÓN 9: WIZARDS SIMPLIFICADOS PARA OPERACIONES ESPECÍFICAS
# WIZARD 1: FishingCheckpointWizard - Puntos de Control GPS
class FishingCheckpointWizard(models.TransientModel):
    """
    WIZARD: FishingCheckpointWizard - Registrar Puntos de Control GPS
    PROPÓSITO:
    Permite registrar la posición GPS actual del navío como punto de control.
    """
    _name = 'fishing.checkpoint.wizard'
    _description = 'Wizard para Puntos de Control'
    # CAMPOS
    # Navío (se toma del contexto)
    vessel_id = fields.Many2one(
        'fishing.vessel', 
        string='Navío', 
        required=True,
        default=lambda self: self.env.context.get('default_vessel_id')
    )
    # Coordenadas (se sugieren del navío actual)
    latitude = fields.Float(
        string='Latitud', 
        digits=(10, 7), 
        required=True,
        default=lambda self: self.env.context.get('default_latitude')
    )
    longitude = fields.Float(
        string='Longitud', 
        digits=(10, 7), 
        required=True,
        default=lambda self: self.env.context.get('default_longitude')
    )
    # Notas adicionales sobre el punto de control
    notes = fields.Text(string='Notas')
    # MÉTODO DE ACCIÓN
    def action_register_checkpoint(self):
        """
        Registrar punto de control en la bitácora del navío.
        """
        self.ensure_one()
        # Crear registro en la bitácora
        self.env['fishing.vessel.log'].create({
            'vessel_id': self.vessel_id.id,
            'log_date': fields.Datetime.now(),
            'log_type': 'checkpoint',  # Tipo: punto de control
            'latitude': self.latitude,
            'longitude': self.longitude,
            'notes': self.notes or "Punto de control registrado"
        })
        # Cerrar wizard
        return {'type': 'ir.actions.act_window_close'}
# WIZARD 2: FishingFuelWizard - Carga de Combustible
class FishingFuelWizard(models.TransientModel):
    """
    WIZARD: FishingFuelWizard - Registrar Carga de Combustible
    """
    _name = 'fishing.fuel.wizard'
    _description = 'Wizard para Carga de Combustible'
    # CAMPOS
    vessel_id = fields.Many2one(
        'fishing.vessel', 
        string='Navío', 
        required=True,
        default=lambda self: self.env.context.get('default_vessel_id')
    )
    fuel_amount = fields.Float(string='Cantidad (L)', required=True)
    fuel_cost = fields.Float(string='Costo')
    supplier = fields.Char(string='Proveedor')
    notes = fields.Text(string='Notas')
    # MÉTODO DE ACCIÓN
    def action_register_fuel(self):
        """
        Registrar carga de combustible en la bitácora.
        """
        self.ensure_one()
        self.env['fishing.vessel.log'].create({
            'vessel_id': self.vessel_id.id,
            'log_date': fields.Datetime.now(),
            'log_type': 'fuel_loading',  # Tipo: carga de combustible
            'notes': f"Carga de {self.fuel_amount}L. Costo: {self.fuel_cost}. {self.notes}"
        })
        return {'type': 'ir.actions.act_window_close'}
# WIZARD 3: FishingSuppliesWizard - Carga de Provisiones
class FishingSuppliesWizard(models.TransientModel):
    """
    WIZARD: FishingSuppliesWizard - Registrar Carga de Provisiones
    """
    _name = 'fishing.supplies.wizard'
    _description = 'Wizard para Carga de Provisiones'
    # CAMPOS
    vessel_id = fields.Many2one(
        'fishing.vessel', 
        string='Navío', 
        required=True,
        default=lambda self: self.env.context.get('default_vessel_id')
    )
    # Tipo de provisiones
    supplies_type = fields.Selection(
        selection=[
            ('food', 'Alimentos'),
            ('water', 'Agua'),
            ('ice', 'Hielo'),
            ('fishing_gear', 'Equipo de Pesca'),
            ('safety', 'Equipo de Seguridad'),
            ('medical', 'Suministros Médicos'),
            ('other', 'Otros')
        ], 
        string='Tipo de Provisiones', 
        required=True
    )
    quantity = fields.Float(string='Cantidad', required=True)
    unit = fields.Char(string='Unidad', default='kg')  # kg, litros, cajas, etc.
    notes = fields.Text(string='Notas')
    # MÉTODO DE ACCIÓN
    def action_register_supplies(self):
        """
        Registrar carga de provisiones en la bitácora.
        """
        self.ensure_one()
        # Obtener nombre legible del tipo de provisiones
        supply_type = dict(self._fields['supplies_type'].selection).get(self.supplies_type)
        # Crear registro
        self.env['fishing.vessel.log'].create({
            'vessel_id': self.vessel_id.id,
            'log_date': fields.Datetime.now(),
            'log_type': 'supply_loading',  # Tipo: carga de provisiones
            'notes': f"Carga: {self.quantity}{self.unit} de {supply_type}. {self.notes}"
        })
        return {'type': 'ir.actions.act_window_close'}
# WIZARD 4: FishingCrewWizard - Cambio de Tripulación
class FishingCrewWizard(models.TransientModel):
    """
    WIZARD: FishingCrewWizard - Registrar Cambio de Tripulación
    """
    _name = 'fishing.crew.wizard'
    _description = 'Wizard para Cambio de Tripulación'
    # CAMPOS
    vessel_id = fields.Many2one(
        'fishing.vessel', 
        string='Navío', 
        required=True,
        default=lambda self: self.env.context.get('default_vessel_id')
    )
    # Tipo de cambio de tripulación
    change_type = fields.Selection(
        selection=[
            ('boarding', 'Embarque'),
            ('disembarking', 'Desembarque'),
            ('captain_change', 'Cambio de Capitán'),
            ('complete_change', 'Cambio Completo')
        ], 
        string='Tipo de Cambio', 
        required=True
    )
    crew_count = fields.Integer(string='Número de Tripulantes', required=True)
    notes = fields.Text(string='Detalles')
    # MÉTODO DE ACCIÓN
    def action_register_crew_change(self):
        """
        Registrar cambio de tripulación en la bitácora.
        """
        self.ensure_one()    
        # Obtener nombre legible del tipo de cambio
        change_type = dict(self._fields['change_type'].selection).get(self.change_type)
        # Crear registro
        self.env['fishing.vessel.log'].create({
            'vessel_id': self.vessel_id.id,
            'log_date': fields.Datetime.now(),
            'log_type': 'crew_change',  # Tipo: cambio de tripulación
            'notes': f"{change_type} de {self.crew_count} tripulantes. {self.notes}"
        })
        return {'type': 'ir.actions.act_window_close'}
# WIZARD 5: FishingInspectionWizard - Inspecciones
class FishingInspectionWizard(models.TransientModel):
    """
    WIZARD: FishingInspectionWizard - Registrar Inspecciones Técnicas
    """
    _name = 'fishing.inspection.wizard'
    _description = 'Wizard para Inspección'
    # CAMPOS
    vessel_id = fields.Many2one(
        'fishing.vessel', 
        string='Navío', 
        required=True,
        default=lambda self: self.env.context.get('default_vessel_id')
    )
    # Tipo de inspección
    inspection_type = fields.Selection(
        selection=[
            ('safety', 'Seguridad'),
            ('mechanical', 'Mecánica'),
            ('sanitary', 'Sanitaria'),
            ('regular', 'Regular')
        ], 
        string='Tipo de Inspección', 
        required=True
    )
    inspector = fields.Char(string='Inspector', required=True)
    result = fields.Selection(
        selection=[
            ('approved', 'Aprobado'),
            ('conditional', 'Condicional'),
            ('failed', 'No Aprobado')
        ], 
        string='Resultado', 
        required=True
    )
    notes = fields.Text(string='Notas')
    # MÉTODO DE ACCIÓN
    def action_register_inspection(self):
        """
        Registrar inspección en la bitácora.
        """
        self.ensure_one()
        # Obtener nombres legibles de los campos de selección
        inspection_type = dict(self._fields['inspection_type'].selection).get(self.inspection_type)
        result = dict(self._fields['result'].selection).get(self.result)
        # Crear registro
        self.env['fishing.vessel.log'].create({
            'vessel_id': self.vessel_id.id,
            'log_date': fields.Datetime.now(),
            'log_type': 'inspection',  # Tipo: inspección
            'notes': f"Inspección {inspection_type} por {self.inspector}. Resultado: {result}. {self.notes}"
        })
        return {'type': 'ir.actions.act_window_close'}
# WIZARD 6: FishingEmergencyWizard - Emergencias
class FishingEmergencyWizard(models.TransientModel):
    """
    WIZARD: FishingEmergencyWizard - Registrar Situaciones de Emergencia
    NOTA: Este wizard tiene diseño visual especial (botón rojo)
    para indicar alta prioridad/urgencia.
    """
    _name = 'fishing.emergency.wizard'
    _description = 'Wizard para Emergencia'
    # CAMPOS
    vessel_id = fields.Many2one(
        'fishing.vessel', 
        string='Navío', 
        required=True,
        default=lambda self: self.env.context.get('default_vessel_id')
    )
    # Tipo de emergencia
    emergency_type = fields.Selection(
        selection=[
            ('medical', 'Médica'),
            ('mechanical', 'Mecánica'),
            ('weather', 'Climática'),
            ('security', 'Seguridad'),
            ('other', 'Otra')
        ], 
        string='Tipo de Emergencia', 
        required=True
    )
    
    # Severidad de la emergencia
    severity = fields.Selection(
        selection=[
            ('low', 'Baja'),
            ('medium', 'Media'),
            ('high', 'Alta')
        ], 
        string='Severidad', 
        required=True
    )
    # Descripción detallada de la emergencia
    description = fields.Text(string='Descripción', required=True)
    # MÉTODO DE ACCIÓN
    def action_register_emergency(self):
        """
        Registrar emergencia en la bitácora.
        NOTA: Las emergencias se registran con formato especial
        para destacar su importancia en el historial.
        """
        self.ensure_one()
        # Obtener nombres legibles
        emergency_type = dict(self._fields['emergency_type'].selection).get(self.emergency_type)
        severity = dict(self._fields['severity'].selection).get(self.severity)
        # Crear registro con formato destacado
        self.env['fishing.vessel.log'].create({
            'vessel_id': self.vessel_id.id,
            'log_date': fields.Datetime.now(),
            'log_type': 'emergency',  # Tipo: emergencia
            # Notas con formato especial para destacar la emergencia
            'notes': f"EMERGENCIA {severity.upper()}: {emergency_type}. {self.description[:100]}..."
            # Se limita a 100 caracteres para evitar registros demasiado largos
        })
        return {'type': 'ir.actions.act_window_close'}
# SECCIÓN 10: WIZARD DE REPORTES GRÁFICOS - FishingReportWizard
class FishingReportWizard(models.TransientModel):
    """
    WIZARD: FishingReportWizard - Generar Reportes Gráficos con Matplotlib
    TIPOS DE REPORTE:
    1. by_species: Captura total por especie (gráfico de barras)
    2. by_zone: Captura total por zona (gráfico de barras)
    3. daily_trend: Tendencia diaria de capturas (gráfico de líneas)
    """
    _name = 'fishing.report.wizard'
    _description = 'Wizard de Reportes de Pesca'
    # CAMPOS DE PARÁMETROS (ENTRADA DEL USUARIO)
    # Rango de fechas para filtrar
    date_from = fields.Date(string='Desde', default=fields.Date.context_today)
    date_to = fields.Date(string='Hasta', default=fields.Date.context_today)
    # Filtro opcional por zona específica
    zone_id = fields.Many2one('fishing.zone', string='Zona Específica')
    # Filtro opcional por especie
    species = fields.Selection(
        selection=[
            ('tuna', 'Atún'),
            ('sardine', 'Sardina'),
            ('shrimp', 'Camarón'),
            ('other', 'Otros')
        ], 
        string='Especie'
    )
    # Tipo de reporte a generar (selección obligatoria)
    report_type = fields.Selection(
        selection=[
            ('by_species', 'Captura por Especie'),
            ('by_zone', 'Captura por Zona'),
            ('daily_trend', 'Tendencia Diaria')
        ], 
        string='Tipo de Reporte', 
        required=True, 
        default='by_species'  # Valor por defecto
    )

    # CAMPOS DE RESULTADO (SALIDA)
    # Imagen del gráfico generado (campo Binary para almacenar PNG)
    report_image = fields.Binary(string='Gráfico Generado', attachment=False)
    # Nombre del archivo de imagen
    report_filename = fields.Char(string='Nombre Archivo')
    # Datos resumidos en texto (estadísticas básicas)
    report_data = fields.Text(string='Datos Resumidos', readonly=True)
    # MÉTODOS ONCHANGE
    @api.onchange('report_type')
    def _onchange_report_type(self):
        """
        REACCIONAR AL CAMBIO DE TIPO DE REPORTE
        Cuando el usuario cambia el tipo de reporte, se limpian
        los campos de resultado para evitar mostrar datos antiguos.
        """
        # Establecer a False para limpiar el campo Binary y Text en la interfaz
        self.report_image = False
        self.report_data = False
        self.report_filename = False
    # MÉTODO PRINCIPAL: GENERAR REPORTE
    def generate_report(self):
        """
        MÉTODO PRINCIPAL: GENERAR EL GRÁFICO CON MATPLOTLIB
        Raises:
            exceptions.UserError: Si no hay datos para los criterios seleccionados
        """
        # Asegurar que solo se procesa un registro del wizard
        self.ensure_one()
        # PASO 1: CONSTRUIR DOMINIO DE BÚSQUEDA
        # Dominio base: rango de fechas
        domain = [
            ('log_date', '>=', self.date_from),
            ('log_date', '<=', self.date_to)
        ]
        # Agregar filtro por zona si se especificó
        if self.zone_id:
            domain.append(('zone_id', '=', self.zone_id.id))
        # Agregar filtro por especie si se especificó
        if self.species:
            domain.append(('species', '=', self.species))
        # PASO 2: BUSCAR REGISTROS DE BITÁCORA
        # Buscar registros que cumplan con el dominio
        logs = self.env['fishing.vessel.log'].search(domain)
        # Validar que hay datos para procesar
        if not logs:
            raise exceptions.UserError("No hay datos de pesca para los criterios seleccionados.")
        # PASO 3: PREPARAR DATOS SEGÚN TIPO DE REPORTE
        # Diccionario para agrupar datos
        data_map = {}
        # 3.1 REPORTE POR ESPECIE
        if self.report_type == 'by_species':
            for log in logs:
                # Obtener nombre legible de la especie
                # CORRECCIÓN: Usar dict para obtener nombre, con valor por defecto
                key = dict(log._fields['species'].selection).get(log.species, 'Sin Especie')
                data_map[key] = data_map.get(key, 0) + log.catch_kg
            # Configurar etiquetas para el gráfico
            xlabel = 'Especie'
            ylabel = 'Captura (Kg)'
            title = 'Captura Total por Especie'
            # 3.2 REPORTE POR ZONA
        elif self.report_type == 'by_zone':
            for log in logs:
                # Usar nombre de la zona, o 'Sin Zona' si no tiene
                key = log.zone_id.name if log.zone_id else 'Sin Zona' 
                data_map[key] = data_map.get(key, 0) + log.catch_kg    
            xlabel = 'Zona'
            ylabel = 'Captura (Kg)'
            title = 'Captura Total por Zona'
        # 3.3 REPORTE DE TENDENCIA DIARIA
        elif self.report_type == 'daily_trend':
            for log in logs:
                # Convertir datetime a string de fecha para agrupar por día
                key = log.log_date.strftime('%Y-%m-%d')
                data_map[key] = data_map.get(key, 0) + log.catch_kg
            # Ordenar por fecha (claves del diccionario)
            data_map = dict(sorted(data_map.items()))
            xlabel = 'Fecha'
            ylabel = 'Captura (Kg)'
            title = 'Tendencia Diaria de Capturas'
        # Validar que se obtuvieron datos
        if not data_map:
             raise exceptions.UserError("No se pudieron agrupar datos válidos para el gráfico.")
        # PASO 4: CREAR GRÁFICO CON MATPLOTLIB
        # Crear figura de matplotlib
        fig = plt.figure(figsize=(10, 6))
        # Agregar subplot (1 fila, 1 columna, posición 1)
        ax = fig.add_subplot(111)
        # Extraer etiquetas y valores del diccionario
        etiquetas = list(data_map.keys())
        valores = list(data_map.values())
        # Paleta de colores personalizada (colores de matplotlib)
        colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', '#8c564b']
        # 4.1 GRÁFICO DE BARRAS (para reportes por especie o zona)
        if self.report_type in ['by_species', 'by_zone']:
            # Crear gráfico de barras
            bars = ax.bar(etiquetas, valores, color=colors[:len(etiquetas)])
            # Agregar etiquetas encima de cada barra con formato sin decimales
            ax.bar_label(bars, fmt='%.0f kg')
            # Rotar etiquetas del eje X 45 grados para mejor legibilidad
            plt.xticks(rotation=45, ha='right')
        # 4.2 GRÁFICO DE LÍNEAS (para tendencia diaria)
        else:  # daily_trend
            # Crear gráfico de líneas con marcadores circulares
            ax.plot(etiquetas, valores, marker='o', linestyle='-', color='#1f77b4')
            # Rotar etiquetas de fecha
            plt.xticks(rotation=45, ha='right')
            # Agregar cuadrícula sutil
            ax.grid(True, linestyle='--', alpha=0.7)
        # Configurar etiquetas de ejes y título
        ax.set_xlabel(xlabel)
        ax.set_ylabel(ylabel)
        ax.set_title(title)
        # Ajustar layout para que no se corten las etiquetas
        plt.tight_layout()
        # PASO 5: GUARDAR EN BUFFER DE MEMORIA
        # Crear buffer de memoria (BytesIO) para guardar la imagen
        buf = io.BytesIO()
        # Guardar figura en el buffer como PNG
        plt.savefig(buf, format='png', dpi=100)
        # Mover al inicio del buffer
        buf.seek(0)
        # Obtener contenido binario del buffer
        image_content = buf.getvalue()
        # Cerrar el buffer
        buf.close()
        # Limpiar matplotlib para liberar memoria
        plt.close('all')
        # PASO 6: GUARDAR EN BASE DE DATOS
        # Escribir resultados en los campos del wizard
        self.write({
            # Codificar imagen en base64 para almacenar en campo Binary
            'report_image': base64.b64encode(image_content),
            # Nombre del archivo basado en tipo de reporte
            'report_filename': f'reporte_{self.report_type}.png',
            # Datos resumidos en texto
            'report_data': f"Datos procesados: {len(logs)} registros. Total Kg: {sum(valores)}"
        })
        # PASO 7: RETORNAR ACCIÓN PARA REFRESCAR LA VISTA
        # Retornar acción para volver a abrir el mismo wizard con los resultados
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'fishing.report.wizard',
            'res_id': self.id,  # ID del registro actual del wizard
            'view_mode': 'form',
            'target': 'new',  # Mantener como ventana emergente
        }
    # MÉTODOS ADICIONALES
    def action_download_report(self):
        """
        PERMITIR DESCARGAR LA IMAGEN GENERADA
        Retorna una acción URL que permite descargar la imagen
        directamente desde el navegador.
        """
        self.ensure_one()
        # Construir URL para descargar el contenido del campo Binary
        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content?model=fishing.report.wizard&id={self.id}&field=report_image&download=true&filename={self.report_filename}',
            'target': 'self',  # Abrir en la misma ventana/descargar
        }
    def action_test_chart(self):
        """
        GENERAR UN GRÁFICO DE PRUEBA SIMPLE
        Método para pruebas/debugging que genera un gráfico simple
        sin leer datos de la base de datos.
        """
        # Crear figura simple
        fig = plt.figure(figsize=(6, 4))
        # Datos de prueba
        plt.plot([1, 2, 3, 4], [10, 20, 25, 30], label='Prueba')
        plt.title("Gráfico de Prueba")
        plt.legend()
        # Guardar en buffer
        buf = io.BytesIO()
        plt.savefig(buf, format='png')
        buf.seek(0)
        content = buf.getvalue()
        buf.close()
        # Limpiar matplotlib
        plt.close('all')
        # Guardar en wizard
        self.write({
            'report_image': base64.b64encode(content),
            'report_filename': 'test.png',
            'report_data': 'Gráfico de prueba generado.'
        })
        # Retornar acción para recargar
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'fishing.report.wizard',
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }