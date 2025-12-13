{
    'name': 'Pesca2',
    'version': '18.0.0.1',
    'description': 'modulo gestion pesca',
    'summary': '',
    'author': 'ESGD',
    'website': 'www.exmaple.com',
    'license': 'LGPL-3',
    'category': '',
    'depends': [
        'base',
        'mail',
        'web'
    ],
    'data': [
        'views/fishing_view.xml',
        'security/ir.model.access.csv',
    ],
    'demo': [
        ''
    ],
    'assets': {
        'web.assets_backend': [
            'https://unpkg.com/leaflet@1.9.4/dist/leaflet.css',
            'https://unpkg.com/leaflet@1.9.4/dist/leaflet.js',

            'pesca2/static/src/js/zone_map_widget.js',
            'pesca2/static/src/xml/zone_map_widget.xml',
            'pesca2/static/src/css/zone_map_widget.css',
        ],
    },
    'auto_install': False,
    'application': True,
    'installable': True,
    'post_init_hook': 'post_init_hook',
}