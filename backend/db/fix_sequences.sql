-- Script pour réparer les séquences PostgreSQL
-- Ce script synchronise toutes les séquences auto-increment avec les valeurs maximales actuelles des tables

-- Réparer la séquence de la table stations
SELECT setval('stations_id_seq', COALESCE((SELECT MAX(id) FROM stations), 1), false);

-- Réparer la séquence de la table pistes
SELECT setval('pistes_id_seq', COALESCE((SELECT MAX(id) FROM pistes), 1), false);

-- Réparer la séquence de la table snow_measures
SELECT setval('snow_measures_id_seq', COALESCE((SELECT MAX(id) FROM snow_measures), 1), false);

-- Afficher les valeurs actuelles des séquences
SELECT 'stations_id_seq' as sequence_name, last_value, is_called FROM stations_id_seq
UNION ALL
SELECT 'pistes_id_seq', last_value, is_called FROM pistes_id_seq
UNION ALL
SELECT 'snow_measures_id_seq', last_value, is_called FROM snow_measures_id_seq;

-- Note:
-- Ce problème arrive généralement quand des données sont insérées manuellement
-- avec des IDs spécifiques (via INSERT INTO ... VALUES (id, ...))
-- au lieu de laisser PostgreSQL gérer automatiquement les IDs.
