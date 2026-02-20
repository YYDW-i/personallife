from django.db import migrations

class Migration(migrations.Migration):
    dependencies = [
        ("news", "0001_initial"),
    ]

    operations = [
        migrations.RunSQL(
            sql=[
                """
                CREATE TABLE IF NOT EXISTS "news_newssource_topics" (
                    "id" integer NOT NULL PRIMARY KEY AUTOINCREMENT,
                    "newssource_id" bigint NOT NULL
                        REFERENCES "news_newssource" ("id")
                        DEFERRABLE INITIALLY DEFERRED,
                    "topic_id" bigint NOT NULL
                        REFERENCES "news_topic" ("id")
                        DEFERRABLE INITIALLY DEFERRED
                );
                """,
                """
                CREATE UNIQUE INDEX IF NOT EXISTS "news_newssource_topics_uniq"
                ON "news_newssource_topics" ("newssource_id", "topic_id");
                """,
                """
                CREATE INDEX IF NOT EXISTS "news_newssource_topics_newssource_id_idx"
                ON "news_newssource_topics" ("newssource_id");
                """,
                """
                CREATE INDEX IF NOT EXISTS "news_newssource_topics_topic_id_idx"
                ON "news_newssource_topics" ("topic_id");
                """,
            ],
            reverse_sql='DROP TABLE IF EXISTS "news_newssource_topics";',
        )
    ]