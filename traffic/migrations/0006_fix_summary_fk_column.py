from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("traffic", "0005_alter_trafficsurveyoverall_options_and_more"),
    ]

    operations = [
        migrations.RunSQL(
            sql="""
                DO $$
                BEGIN
                  IF EXISTS (
                    SELECT 1 FROM information_schema.columns
                    WHERE table_name = 'traffic_survey_summary' AND column_name = 'survey_id'
                  ) AND NOT EXISTS (
                    SELECT 1 FROM information_schema.columns
                    WHERE table_name = 'traffic_survey_summary' AND column_name = 'traffic_survey_id'
                  ) THEN
                    ALTER TABLE traffic_survey_summary RENAME COLUMN survey_id TO traffic_survey_id;
                  END IF;

                  IF NOT EXISTS (
                    SELECT 1 FROM information_schema.columns
                    WHERE table_name = 'traffic_survey_summary' AND column_name = 'traffic_survey_id'
                  ) THEN
                    ALTER TABLE traffic_survey_summary
                    ADD COLUMN IF NOT EXISTS traffic_survey_id bigint;
                  END IF;

                  IF NOT EXISTS (
                    SELECT 1 FROM pg_constraint WHERE conname = 'traffic_survey_summary_traffic_survey_id_fk'
                  ) THEN
                    ALTER TABLE traffic_survey_summary
                    ADD CONSTRAINT traffic_survey_summary_traffic_survey_id_fk
                    FOREIGN KEY (traffic_survey_id)
                    REFERENCES traffic_survey(traffic_survey_id)
                    DEFERRABLE INITIALLY DEFERRED;
                  END IF;
                END$$;
            """,
            reverse_sql="""
                ALTER TABLE traffic_survey_summary
                DROP CONSTRAINT IF EXISTS traffic_survey_summary_traffic_survey_id_fk;
                ALTER TABLE traffic_survey_summary
                DROP COLUMN IF EXISTS traffic_survey_id;
            """,
        ),
    ]
