// IMPORTACIONES DE BIBLIOTECAS Y MÓDULOS DE ODOO
// Importa el registro global de Odoo para registrar nuevos tipos de campos
import { registry } from "@web/core/registry";
// Importa propiedades estándar que todos los campos de Odoo deben tener
import { standardFieldProps } from "@web/views/fields/standard_field_props"; 
// Importa componentes y hooks de OWL (Odoo Web Library)
import { Component, useRef, useEffect } from "@odoo/owl";
// CLASE PRINCIPAL DEL WIDGET: ZoneMapWidget
/**
 * WIDGET PERSONALIZADO DE MAPA LEAFLET
 * 
 * Esta clase define un widget de campo personalizado para Odoo que:
 * - Muestra un mapa interactivo usando Leaflet.js
 * - Sincroniza con campos de latitud y longitud en el modelo
 * - Permite edición arrastrando el marcador o haciendo clic (si no es readonly)
 * - Se actualiza automáticamente cuando cambian las coordenadas
 */
export class ZoneMapWidget extends Component {
    // MÉTODO setup() - INICIALIZACIÓN DEL COMPONENTE
    /**
     * Método setup - Se ejecuta cuando se inicializa el componente
     * Configura referencias, estado inicial y efectos reactivos
     */
    setup() {
    // 1. CREAR REFERENCIAS A ELEMENTOS DEL DOM
    // Crea una referencia al elemento del contenedor del mapa
    // "mapContainer" debe coincidir con t-ref en el template XML
    // this.mapRef.el proporciona acceso directo al elemento DOM
        this.mapRef = useRef("mapContainer");    
        // Variable para almacenar la instancia del mapa Leaflet
        // Inicialmente null porque el mapa no se ha creado aún
        this.mapInstance = null;
        // Variable para almacenar el marcador en el mapa
        // Inicialmente null porque el marcador no se ha creado aún
        this.marker = null;
        // 2. CONFIGURAR EFECTO REACTIVO CON useEffect
        /**
         * useEffect - Hook de OWL que ejecuta código cuando cambian dependencias
         * 
         * Primer parámetro (función): Código a ejecutar cuando cambian las dependencias
         *   - Renderiza el mapa cuando se monta el componente
         *   - Retorna función de limpieza que se ejecuta al desmontar
         * 
         * Segundo parámetro (función): Array de dependencias que activan el efecto
         *   - Se vuelve a ejecutar cuando cambian la latitud o longitud
         */
        useEffect(
            // Función que se ejecuta cuando cambian las dependencias
            () => {
                // Renderizar o actualizar el mapa Leaflet
                this.renderLeafletMap();
                // Función de limpieza que se ejecuta al desmontar el componente
                return () => {
                    // Si existe una instancia del mapa, eliminarla para liberar memoria
                    if (this.mapInstance) {
                        this.mapInstance.remove();  // Método Leaflet para eliminar mapa
                        this.mapInstance = null;    // Liberar referencia para garbage collection
                    }
                };
            },
            // Array de dependencias: se ejecuta cuando cambian estas propiedades
            () => [this.props.record.data.latitude, this.props.record.data.longitude]
        );
    }
    // GETTERS PARA ACCEDER A LAS COORDENADAS ACTUALES
    
    /**
     * Getter para obtener la latitud actual
     * @returns {number} Latitud del registro o 0 si no está definida
     */
    get lat() {
        // Accede a los datos del registro actual a través de props
        // Si latitude es undefined/null/0, retorna 0 como valor por defecto
        return this.props.record.data.latitude || 0;
    }
    /**
     * Getter para obtener la longitud actual
     * @returns {number} Longitud del registro o 0 si no está definida
     */
    get lng() {
        // Accede a los datos del registro actual a través de props
        // Si longitude es undefined/null/0, retorna 0 como valor por defecto
        return this.props.record.data.longitude || 0;
    }
    // MÉTODO PRINCIPAL: renderLeafletMap()
    /**
     * Renderiza o actualiza el mapa Leaflet
     * 
     * Este método:
     * 1. Verifica que Leaflet esté cargado y que el contenedor exista
     * 2. Crea el mapa por primera vez o actualiza uno existente
     * 3. Configura tiles (capas de mapa) de OpenStreetMap
     * 4. Crea y configura el marcador
     * 5. Configura eventos para edición (si no es readonly)
     * 6. Ajusta el tamaño del mapa
     */
    renderLeafletMap() {
    // 1. VERIFICACIONES PREVIAS
    // Verificar que la biblioteca Leaflet esté cargada globalmente
    // typeof L === 'undefined': Leaflet se carga globalmente como variable "L"
    // !this.mapRef.el: Verificar que el elemento contenedor exista en el DOM
        if (typeof L === 'undefined' || !this.mapRef.el) {
            // Salir silenciosamente si no se cumplen las condiciones
            // Esto puede pasar durante la renderización inicial
            return;
        }
        // Obtener referencias a elementos y datos necesarios
        const el = this.mapRef.el;               // Elemento DOM del contenedor
        const lat = this.lat;                    // Latitud actual (del getter)
        const lng = this.lng;                    // Longitud actual (del getter)
        // Determinar si el marcador debe ser arrastrable
        // Si el campo es readonly, no se puede editar (arrastrar)
        const isDraggable = !this.props.readonly;
        // 2. CREAR MAPA POR PRIMERA VEZ
        // // Si el mapa no existe (primera vez que se renderiza)
        if (!this.mapInstance) {
            // Asegurar que el contenedor tenga altura
            // A veces el elemento puede tener height: 0 durante la renderización
            if (el.clientHeight === 0) {
                el.style.height = "300px";  // Forzar altura mínima
            } 
            // 2.1 CREAR INSTANCIA DEL MAPA LEAFLET
            // L.map() crea una nueva instancia del mapa en el elemento el
            // .setView([lat, lng], 13): Centra el mapa en las coordenadas con zoom 13
            // Zoom 13 es un nivel moderado que muestra detalles de ciudad
            this.mapInstance = L.map(el).setView([lat, lng], 5);            
            // 2.2 AGREGAR CAPA DE TILES (IMÁGENES DEL MAPA)
            /**
             * L.tileLayer() crea una capa de mosaicos (tiles) de OpenStreetMap
             * URL: 'https://{s}.tile.openslisttmap.org/{z}/{x}/{y}.png'
             *   - {s}: Subdominio (a, b, c) para balancear carga
             *   - {z}: Nivel de zoom
             *   - {x}, {y}: Coordenadas del tile
             * 
             * options:
             *   - maxZoom: 19: Zoom máximo permitido
             *   - attribution: Texto de atribución requerido por OpenStreetMap
             * 
             * .addTo(this.mapInstance): Agrega la capa al mapa
             */
            L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
                maxZoom: 19,
                attribution: '© OpenStreeMap'  
            }).addTo(this.mapInstance);
            // 2.3 CREAR Y CONFIGURAR MARCADOR
            /**
             * L.marker() crea un marcador en la posición especificada
             * [lat, lng]: Coordenadas iniciales del marcador
             * { draggable: isDraggable }: Hace el marcador arrastrable según permisos
             * .addTo(this.mapInstance): Agrega el marcador al mapa
             */
            this.marker = L.marker([lat, lng], { draggable: isDraggable }).addTo(this.mapInstance);
            // 2.4 CONFIGURAR EVENTOS DE EDICIÓN (SI ES EDITABLE)
            // Solo configurar eventos si el marcador es arrastrable (no readonly)
            if (isDraggable) {
                /**
                 * 2.4.1 EVENTO: dragend (terminar de arrastrar)
                 * Se dispara cuando el usuario suelta el marcador después de arrastrarlo
                 */
                this.marker.on('dragend', (e) => {
                    // Obtener la nueva posición del marcador
                    const newLatLng = this.marker.getLatLng();
                    // Actualizar las coordenadas en el registro de Odoo
                    this.updateCoordinates(newLatLng.lat, newLatLng.lng);
                });
                /**2.4.2 EVENTO: click en el mapa
                 * Se dispara cuando el usuario hace clic en cualquier parte del mapa
                 */
                this.mapInstance.on('click', (e) => {
                    // e.latlng contiene las coordenadas del clic
                    const { lat, lng } = e.latlng; 
                    // Mover el marcador a la posición del clic
                    this.marker.setLatLng([lat, lng]);
                    // Actualizar las coordenadas en el registro de Odoo
                    this.updateCoordinates(lat, lng);
                });
            }
        // 3. ACTUALIZAR MAPA EXISTENTE
        } else {
            // Si el mapa ya existe, solo actualizar la vista y el marcador
            // Mover el centro del mapa a las nuevas coordenadas
            this.mapInstance.setView([lat, lng], 13);
            // Si existe el marcador, actualizar su posición
            if (this.marker) {
                this.marker.setLatLng([lat, lng]);
            }
        }
        // 4. AJUSTAR TAMAÑO DEL MAPA (INVALIDATE SIZE)
        /**
         * Leaflet necesita recalcular el tamaño del mapa después de cambios en el DOM
         * setTimeout con 200ms da tiempo a que se complete la renderización
         * this.mapInstance.invalidateSize() recalcula dimensiones del mapa
         */
        setTimeout(() => {
            // Verificar que el mapa todavía exista (evitar errores si se desmontó)
            if (this.mapInstance) {
                this.mapInstance.invalidateSize();
            }
        }, 200);
    }
    // MÉTODO: updateCoordinates()
    /**
     * Actualiza las coordenadas en el registro de Odoo
     * 
     * Este método:
     * 1. Normaliza las coordenadas (especialmente la longitud)
     * 2. Redondea a una precisión específica
     * 3. Actualiza los campos en el registro actual de Odoo
     * @param {number} lat - Nueva latitud
     * @param {number} lng - Nueva longitud
     */
    updateCoordinates(lat, lng) {
       // 1. CONFIGURACIÓN DE PRECISIÓN
       // Número de decimales a mantener (7 decimales ≈ 1.1 cm de precisión)
        const DECIMAL_PLACES = 7; 
        // Convertir a números flotantes (por si vienen como strings)
        let finalLat = parseFloat(lat);
        let finalLng = parseFloat(lng);
        // 2. NORMALIZAR LONGITUD AL RANGO [-180, 180]
        // La longitud debe estar entre -180 y 180 grados
        // Estos bucles corrigen valores fuera de rango (ej: 190 → -170)
        while (finalLng > 180) finalLng -= 360;
        while (finalLng < -180) finalLng += 360;
        // 3. REDONDEAR A PRECISIÓN ESPECIFICADA
        // toFixed(DECIMAL_PLACES) convierte a string con N decimales
        // parseFloat() convierte de nuevo a número
        finalLat = parseFloat(finalLat.toFixed(DECIMAL_PLACES));
        finalLng = parseFloat(finalLng.toFixed(DECIMAL_PLACES));
        // 4. LOG PARA DEPURACIÓN
        // Muestra en consola qué coordenadas se están actualizando
        // Útil para desarrollo y depuración
        console.log(`[MAP] Actualizando Odoo: Lat=${finalLat}, Lng=${finalLng}`);
        // 5. ACTUALIZAR REGISTRO EN ODOO
        // Verificar que exista el registro (props.record)
        if (this.props.record) {
            // this.props.record.update() actualiza los campos en el registro actual
            // Esto disparará guardado automático y notificará a otros componentes
            this.props.record.update({
                latitude: finalLat,   // Actualizar campo de latitud
                longitude: finalLng,  // Actualizar campo de longitud
            });
        }
    }
}
// CONFIGURACIÓN DEL COMPONENTE: TEMPLATE Y PROPS
/**
 * ESPECIFICAR EL TEMPLATE OWL
 * ZoneMapWidget.template debe coincidir con t-name en el archivo XML
 * "pesca2.ZoneMapWidget" busca el template con ese nombre
 */
ZoneMapWidget.template = "pesca2.ZoneMapWidget";
/**
 * DEFINIR PROPIEDADES (PROPS) DEL COMPONENTE
 * Los props son las propiedades que el componente acepta
 * ...standardFieldProps: Incluye todas las props estándar de campos Odoo:
 *   - record: El registro actual que se está editando
 *   - readonly: Si el campo es de solo lectura
 *   - options: Opciones adicionales pasadas desde XML
 */
ZoneMapWidget.props = {
    ...standardFieldProps,  // Propiedades estándar de campos Odoo
};
// REGISTRAR EL WIDGET EN EL SISTEMA DE CAMPOS DE ODOO
/**
 * REGISTRAR WIDGET PERSONALIZADO
 * 
 * registry.category("fields"): Accede al registro de tipos de campo
 * .add("zone_leaflet_map", {...}): Agrega un nuevo tipo de campo llamado "zone_leaflet_map"
 * 
 * Cuando en XML se usa widget="zone_leaflet_map", Odoo buscará aquí
 * y usará este componente para renderizar el campo.
 */
registry.category("fields").add("zone_leaflet_map", {
    // component: La clase del componente JavaScript a usar
    component: ZoneMapWidget,
});