from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("traffic", "0001_initial"),
    ]

    operations = [
        migrations.RunSQL(
            sql="""
            ALTER TABLE traffic_survey
            ADD COLUMN IF NOT EXISTS road_id bigint;

            DO $$
            BEGIN
                IF NOT EXISTS (
                    SELECT 1
                    FROM information_schema.table_constraints tc
                    JOIN information_schema.key_column_usage kcu
                        ON tc.constraint_name = kcu.constraint_name
                    WHERE tc.table_name = 'traffic_survey'
                      AND tc.constraint_type = 'FOREIGN KEY'
                      AND kcu.column_name = 'road_id'
                ) THEN
                    ALTER TABLE traffic_survey
                    ADD CONSTRAINT traffic_survey_road_id_fk
                    FOREIGN KEY (road_id)
                    REFERENCES grms_road(road_id)
                    DEFERRABLE INITIALLY DEFERRED;
                END IF;
            END $$;

            DO $$
            BEGIN
                IF EXISTS (
                    SELECT 1
                    FROM information_schema.columns
                    WHERE table_name = 'traffic_survey'
                      AND column_name = 'road_id'
                      AND is_nullable = 'YES'
                ) AND NOT EXISTS (
                    SELECT 1 FROM traffic_survey WHERE road_id IS NULL LIMIT 1
                ) THEN
                    ALTER TABLE traffic_survey
                    ALTER COLUMN road_id SET NOT NULL;
                END IF;
            END $$;
            """,
            reverse_sql="""
            DO $$
            BEGIN
                IF EXISTS (
                    SELECT 1
                    FROM information_schema.table_constraints tc
                    WHERE tc.table_name = 'traffic_survey'
                      AND tc.constraint_name = 'traffic_survey_road_id_fk'
                ) THEN
                    ALTER TABLE traffic_survey DROP CONSTRAINT traffic_survey_road_id_fk;
                END IF;
            END $$;

            ALTER TABLE traffic_survey DROP COLUMN IF EXISTS road_id;
            """,
        ),
    ]
