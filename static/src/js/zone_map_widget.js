/** @odoo-module **/

import { registry } from "@web/core/registry";
import { standardFieldProps } from "@web/views/fields/standard_field_props"; 
import { Component, useRef, useEffect } from "@odoo/owl";

export class ZoneMapWidget extends Component {

    setup() {
        this.mapRef = useRef("mapContainer");
        this.mapInstance = null;
        this.marker = null;
        
        useEffect(
            () => {
                this.renderLeafletMap();
                return () => {
                    if (this.mapInstance) {
                        this.mapInstance.remove();
                        this.mapInstance = null;
                    }
                };
            },
            () => [this.props.record.data.latitude, this.props.record.data.longitude]
        );
    }
    
    get lat() {
        return this.props.record.data.latitude || 0;
    }
    
    get lng() {
        return this.props.record.data.longitude || 0;
    }

    renderLeafletMap() {
        if (typeof L === 'undefined' || !this.mapRef.el) {
            return;
        }

        const el = this.mapRef.el;
        const lat = this.lat;
        const lng = this.lng;
        const isDraggable = !this.props.readonly;

        if (!this.mapInstance) {
            if (el.clientHeight === 0) {
                el.style.height = "500px";
            }
            
            this.mapInstance = L.map(el).setView([lat, lng], 13);
            
            L.tileLayer('https://{s}.tile.openslisttmap.org/{z}/{x}/{y}.png', {
                maxZoom: 19,
                attribution: '© OpenSlisttMap'
            }).addTo(this.mapInstance);

            this.marker = L.marker([lat, lng], { draggable: isDraggable }).addTo(this.mapInstance);
            
            if (isDraggable) {
                this.marker.on('dragend', (e) => {
                    const newLatLng = this.marker.getLatLng();
                    this.updateCoordinates(newLatLng.lat, newLatLng.lng);
                });

                this.mapInstance.on('click', (e) => {
                    const { lat, lng } = e.latlng;
                    this.marker.setLatLng([lat, lng]);
                    this.updateCoordinates(lat, lng);
                });
            }

        } else {
            this.mapInstance.setView([lat, lng], 13);
            if (this.marker) {
                this.marker.setLatLng([lat, lng]);
            }
        }

        setTimeout(() => {
            this.mapInstance.invalidateSize();
        }, 200);
    }
    
    updateCoordinates(lat, lng) {
        const DECIMAL_PLACES = 7; 
        
        let finalLat = parseFloat(lat);
        let finalLng = parseFloat(lng);
        
        while (finalLng > 180) finalLng -= 360;
        while (finalLng < -180) finalLng += 360;

        finalLat = parseFloat(finalLat.toFixed(DECIMAL_PLACES));
        finalLng = parseFloat(finalLng.toFixed(DECIMAL_PLACES));
        
        console.log(`[MAP] Actualizando Odoo: Lat=${finalLat}, Lng=${finalLng}`);
        
        if (this.props.record) {
            this.props.record.update({
                latitude: finalLat,
                longitude: finalLng,
            });
        }
    }
}

ZoneMapWidget.template = "pesca2.ZoneMapWidget";

ZoneMapWidget.props = {
    ...standardFieldProps,
};

registry.category("fields").add("zone_leaflet_map", {
    component: ZoneMapWidget,
});