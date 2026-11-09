INSERT INTO brady.argos_geofence_zones
    (zone_id,zone_name,country,mode,polygon,enabled,source_key)
VALUES
    ('CM_N10_BERTOUA_DIMAKO',
     'Périmètre simulé N10 — secteur Bertoua–Dimako',
     'Cameroun','road',
     '{"type":"Polygon","coordinates":[[[13.63,4.50],[13.68,4.50],[13.68,4.565],[13.63,4.565],[13.63,4.50]]]}',
     TRUE,'ARGOS_GEOFENCE_ZONES')
ON CONFLICT (zone_id) DO UPDATE SET
    zone_name=EXCLUDED.zone_name,country=EXCLUDED.country,mode=EXCLUDED.mode,
    polygon=EXCLUDED.polygon,enabled=TRUE,source_key=EXCLUDED.source_key;
