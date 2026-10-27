CREATE TABLE IF NOT EXISTS brady.argos_geofence_zones (
    zone_id VARCHAR(80) PRIMARY KEY,
    zone_name TEXT NOT NULL,
    country VARCHAR(100) NOT NULL,
    mode VARCHAR(30) NOT NULL,
    polygon JSONB NOT NULL,
    enabled BOOLEAN NOT NULL DEFAULT TRUE,
    source_key VARCHAR(100) NOT NULL DEFAULT 'ARGOS_GEOFENCE_ZONES',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CHECK (jsonb_typeof(polygon) = 'object' AND polygon->>'type' = 'Polygon')
);

INSERT INTO brady.regulatory_sources
    (source_key,title,source_type,authority,jurisdiction,transport_modes,legal_status,
     applicability_conditions,summary,verified_at)
VALUES
('ARGOS_GEOFENCE_ZONES','Zones géographiques opérationnelles configurées dans ARGOS','INTERNAL_RULE','ARGOS','Zones de démonstration et zones configurées',ARRAY['sea','road','multimodal'],'INTERNAL',
 'Une zone est une géométrie opérationnelle configurée; elle ne constitue pas une frontière légale, une zone douanière ou une restriction de circulation.',
 'Les notifications signalent une entrée dans les géométries configurées et ne déterminent pas les règles applicables à la zone.',CURRENT_DATE)
ON CONFLICT (source_key) DO UPDATE SET
    title=EXCLUDED.title, summary=EXCLUDED.summary, updated_at=NOW();

INSERT INTO brady.argos_geofence_zones(zone_id,zone_name,country,mode,polygon) VALUES
('CN_SHANGHAI_PORT','Port de Shanghai — périmètre de démonstration','Chine','sea',
 '{"type":"Polygon","coordinates":[[[121.36,30.80],[121.96,30.80],[121.96,31.52],[121.36,31.52],[121.36,30.80]]]}'),
('SG_STRAIT','Détroit de Singapour — périmètre de démonstration','Singapour','sea',
 '{"type":"Polygon","coordinates":[[[103.50,1.08],[104.12,1.08],[104.12,1.48],[103.50,1.48],[103.50,1.08]]]}'),
('CM_DOUALA_PORT','Port de Douala — périmètre de démonstration','Cameroun','sea',
 '{"type":"Polygon","coordinates":[[[9.62,3.98],[9.80,3.98],[9.80,4.12],[9.62,4.12],[9.62,3.98]]]}'),
('CM_BERTOUA','Bertoua — zone urbaine de démonstration','Cameroun','road',
 '{"type":"Polygon","coordinates":[[[13.64,4.53],[13.74,4.53],[13.74,4.63],[13.64,4.63],[13.64,4.53]]]}'),
('CM_ABONG_MBANG','Abong-Mbang — zone urbaine de démonstration','Cameroun','road',
 '{"type":"Polygon","coordinates":[[[13.13,3.94],[13.23,3.94],[13.23,4.03],[13.13,4.03],[13.13,3.94]]]}'),
('CM_AYOS','Ayos — zone urbaine de démonstration','Cameroun','road',
 '{"type":"Polygon","coordinates":[[[12.45,3.86],[12.57,3.86],[12.57,3.96],[12.45,3.96],[12.45,3.86]]]}'),
('CM_YAOUNDE','Yaoundé — zone urbaine de démonstration','Cameroun','road',
 '{"type":"Polygon","coordinates":[[[11.42,3.76],[11.59,3.76],[11.59,3.95],[11.42,3.95],[11.42,3.76]]]}')
ON CONFLICT (zone_id) DO UPDATE SET
    zone_name=EXCLUDED.zone_name,country=EXCLUDED.country,mode=EXCLUDED.mode,
    polygon=EXCLUDED.polygon,enabled=TRUE;
