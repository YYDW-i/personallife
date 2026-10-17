import ast
from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import Client, TestCase, SimpleTestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from profiles.forms import HealthProfileForm
from profiles.models import HealthProfile
from tasks.models import Task
from maths import engine
from deeplearning.forms import DEFAULT_FORM_DATA, DeepLearningBuilderForm
from deeplearning.views import _normalize_config
from deeplearning.utils.code_generator import generate_pytorch_code
from news.models import NewsSource, NewsItem


class ApplicationRegressionTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = get_user_model().objects.create_user("tester", password="test-password-2026")
        cls.other = get_user_model().objects.create_user("other", password="other-password-2026")

    def setUp(self):
        self.client.force_login(self.user)

    def test_all_main_pages_render(self):
        for path in ("/", "/tasks/", "/tasks/new/", "/calendar/", "/news/", "/news/preferences/",
                     "/maths/", "/deeplearning/", "/analytics/iching/", "/settings/", "/players/profile/"):
            with self.subTest(path=path):
                self.assertEqual(self.client.get(path).status_code, 200)

    def test_private_pages_require_login(self):
        self.client.logout()
        for path in ("/", "/tasks/", "/deeplearning/", "/analytics/iching/"):
            self.assertEqual(self.client.get(path).status_code, 302)

    def test_analytics_root_redirects(self):
        self.assertRedirects(self.client.get("/analytics/"), "/analytics/iching/")

    def test_registration_does_not_log_out_current_user(self):
        self.client.get("/accounts/register/")
        self.assertEqual(int(self.client.session["_auth_user_id"]), self.user.pk)

    def test_create_task_and_complete(self):
        response = self.client.post("/tasks/new/", {"title": "测试任务", "schedule_kind": "NONE", "remind_lead_minutes": 0})
        self.assertEqual(response.status_code, 302)
        task = Task.objects.get(user=self.user)
        self.assertEqual(self.client.get(reverse("tasks:complete", args=[task.pk])).status_code, 405)
        self.client.post(reverse("tasks:complete", args=[task.pk]))
        task.refresh_from_db()
        self.assertEqual(task.status, Task.Status.DONE)

    def test_task_access_is_scoped_to_user(self):
        task = Task.objects.create(user=self.other, title="私有任务")
        for name in ("update", "delete"):
            self.assertEqual(self.client.get(reverse(f"tasks:{name}", args=[task.pk])).status_code, 404)
        self.assertEqual(self.client.post(reverse("tasks:complete", args=[task.pk])).status_code, 404)

    def test_complete_anonymous_redirects(self):
        task = Task.objects.create(user=self.user, title="任务")
        self.client.logout()
        self.assertEqual(self.client.post(reverse("tasks:complete", args=[task.pk])).status_code, 302)

    def test_pending_tasks_before_completed(self):
        Task.objects.create(user=self.user, title="完成", status="DONE")
        todo = Task.objects.create(user=self.user, title="待办")
        self.assertEqual(self.client.get("/tasks/").context["tasks"][0], todo)

    def test_edit_preserves_datetime_and_resets_reminder(self):
        due = timezone.now() + timedelta(days=1)
        task = Task.objects.create(user=self.user, title="提醒", schedule_kind="AT", due_at=due,
                                   remind_enabled=True, reminded_at=timezone.now())
        response = self.client.get(reverse("tasks:update", args=[task.pk]))
        self.assertContains(response, timezone.localtime(due).strftime("%Y-%m-%dT%H:%M"))
        updated = timezone.localtime(due + timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M")
        self.client.post(reverse("tasks:update", args=[task.pk]), {
            "title": "提醒", "schedule_kind": "AT", "due_at": updated,
            "remind_enabled": "on", "remind_lead_minutes": "5"})
        task.refresh_from_db()
        self.assertIsNone(task.reminded_at)
        self.assertEqual(task.remind_at, task.due_at - timedelta(minutes=5))

    def test_reminders_return_once_and_only_own(self):
        due = timezone.now() - timedelta(minutes=1)
        own = Task.objects.create(user=self.user, title="自己的", schedule_kind="AT", due_at=due, remind_enabled=True)
        Task.objects.create(user=self.other, title="别人的", schedule_kind="AT", due_at=due, remind_enabled=True)
        self.assertEqual([item["id"] for item in self.client.get("/tasks/api/reminders/").json()["reminders"]], [own.pk])
        self.assertEqual(self.client.get("/tasks/api/reminders/").json()["reminders"], [])

    def test_focus_can_complete_and_logout(self):
        now = timezone.now()
        task = Task.objects.create(user=self.user, title="专注", schedule_kind="WINDOW",
                                   window_start=now-timedelta(minutes=1), window_end=now+timedelta(minutes=10))
        self.assertEqual(self.client.get("/").status_code, 302)
        self.assertEqual(self.client.get(reverse("tasks:focus", args=[task.pk])).status_code, 200)
        self.client.post(reverse("tasks:complete", args=[task.pk]))
        task.refresh_from_db()
        self.assertEqual(task.status, "DONE")
        task.status = "TODO"
        task.save()
        self.client.post("/accounts/logout/")
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_focus_nonwindow_does_not_crash(self):
        task = Task.objects.create(user=self.user, title="无时间")
        self.assertRedirects(self.client.get(reverse("tasks:focus", args=[task.pk])), "/tasks/")

    def test_invalid_calendar_dates_return_404(self):
        for path in ("/calendar/2026/13/", "/calendar/0/1/", "/calendar/day/2026/2/30/"):
            self.assertEqual(self.client.get(path).status_code, 404)

    def test_cross_day_window_appears_on_both_days(self):
        start = timezone.make_aware(timezone.datetime(2026, 10, 1, 23))
        task = Task.objects.create(user=self.user, title="跨天", schedule_kind="WINDOW",
                                   window_start=start, window_end=start+timedelta(hours=2))
        response = self.client.get("/calendar/2026/10/")
        days = {cell["date_str"]: cell for week in response.context["weeks"] for cell in week}
        self.assertIn(task, days["2026-10-01"]["tasks"])
        self.assertIn(task, days["2026-10-02"]["tasks"])

    @patch("core.views.get_health_analysis")
    def test_dashboard_never_sends_health_data_on_get(self, ai):
        HealthProfile.objects.create(user=self.user, height_cm=175, weight_kg=65, age_year=25,
                                     gender="M", exercise_frequency=3, exercise_time_minutes=30, sleep_hours=7.5)
        self.assertEqual(self.client.get("/").status_code, 200)
        ai.assert_not_called()

    @override_settings(OPENAI_API_KEY="test-only")
    @patch("core.views.get_health_analysis", return_value="生活习惯参考\n保持规律")
    def test_explicit_ai_analysis_is_cached(self, ai):
        profile = HealthProfile.objects.create(user=self.user, height_cm=175, weight_kg=65, age_year=25,
                                               gender="M", exercise_frequency=3, exercise_time_minutes=30, sleep_hours=7.5)
        self.client.post("/")
        profile.refresh_from_db()
        self.assertEqual(profile.ai_status, "保持规律")
        self.client.get("/")
        ai.assert_called_once()

    def test_math_bad_json_returns_400(self):
        for route in ("/maths/api/run/", "/maths/api/eval/", "/maths/api/plot/"):
            for payload in ("{", "[]", "null", '"text"'):
                self.assertEqual(self.client.post(route, data=payload, content_type="application/json").status_code, 400)

    def test_math_api_computes(self):
        response = self.client.post("/maths/api/run/", data={"mode": "diff", "expr": "x^3"}, content_type="application/json")
        self.assertEqual(response.json()["data"]["result_str"], "3*x**2")

    def test_csrf_is_required(self):
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.user)
        self.assertEqual(client.post("/tasks/new/", {"title": "bad"}).status_code, 403)

    @patch("news.services.fetcher.download_feed")
    def test_news_sync_returns_total_and_skips_unsafe_links(self, download):
        from news.services.fetcher import fetch_all_sources
        download.return_value = b'<rss version="2.0"><channel><title>T</title><item><title>A</title><link>https://example.com/a</link><guid>a</guid></item><item><title>B</title><link>javascript:alert(1)</link><guid>b</guid></item></channel></rss>'
        NewsSource.objects.create(name="A", rss_url="https://example.com/rss")
        NewsSource.objects.create(name="B", rss_url="https://example.org/rss")
        self.assertEqual(fetch_all_sources(), 2)
        self.assertEqual(NewsItem.objects.count(), 2)
        self.assertEqual(fetch_all_sources(), 0)

    def test_iching_uses_bundled_data(self):
        response = self.client.post("/analytics/iching/cast-ajax/", {"method": "coins"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()["coin_results"]), 6)

    def test_invalid_iching_method_returns_400(self):
        self.assertEqual(self.client.post("/analytics/iching/cast-ajax/", {"method": "invalid"}).status_code, 400)

    def test_random_iching_method_is_supported(self):
        self.assertEqual(self.client.post("/analytics/iching/cast-ajax/", {"method": "random"}).status_code, 200)


class MathEngineRegressionTests(SimpleTestCase):
    def test_implicit_multiplication(self):
        self.assertEqual(str(engine.safe_parse("2x + 1")), "2*x + 1")

    def test_unsafe_syntax_is_rejected(self):
        for expr in ("().__class__", "getattr(1,2)", "[x for x in (1,2)]", "__import__('os')", "x.real", "10**(10**10)"):
            with self.subTest(expr=expr), self.assertRaises((ValueError, SyntaxError)):
                engine.safe_parse(expr)

    def test_constant_plots(self):
        self.assertTrue(engine.plot_2d("3")["img_base64"])
        self.assertTrue(engine.plot_3d("3")["img_base64"])

    def test_invalid_plot_range(self):
        with self.assertRaises(ValueError):
            engine.plot_2d("x", x_min=5, x_max=-5)

    def test_both_sided_limit(self):
        with self.assertRaises(ValueError):
            engine.limit_expr("1/x", direction="+-")

    def test_partial_integral_bounds_rejected(self):
        with self.assertRaises(ValueError):
            engine.integrate_expr("x", a="0")

    def test_empty_matrix_rejected(self):
        for value in ("[]", "[[]]", "[[1],[1,2]]"):
            with self.assertRaises(ValueError):
                engine.linear_algebra("det", value)

    def test_health_decimals_and_ranges(self):
        data = {"height_cm": "175.5", "weight_kg": "65.5", "age_year": 25, "gender": "M",
                "exercise_frequency": 3, "exercise_time_minutes": 30, "sleep_hours": "7.5"}
        self.assertTrue(HealthProfileForm(data).is_valid())
        for key, value in (("height_cm", 0), ("sleep_hours", 25), ("age_year", -1)):
            self.assertFalse(HealthProfileForm({**data, key: value}).is_valid())

    def test_generated_code_compiles_for_all_models_and_datasets(self):
        for model in ("linear", "mlp", "custom_formula"):
            for dataset in ("normal_regression", "normal_classification", "iris", "breast_cancer", "digits", "mnist", "fashion_mnist"):
                with self.subTest(model=model, dataset=dataset):
                    config = _normalize_config({**DEFAULT_FORM_DATA, "model_name": model, "dataset_name": dataset})
                    ast.parse(generate_pytorch_code(config))

    def test_custom_formula_and_network_sizes_are_validated(self):
        self.assertFalse(DeepLearningBuilderForm({**DEFAULT_FORM_DATA, "model_name": "custom_formula", "custom_formula": "__import__('os')"}).is_valid())
        self.assertFalse(DeepLearningBuilderForm({**DEFAULT_FORM_DATA, "hidden_sizes": "999999999"}).is_valid())

    def test_exported_custom_and_sparse_classification_code_runs(self):
        import contextlib
        import io
        import matplotlib.pyplot as plt
        for model, dataset in (("custom_formula", "normal_regression"), ("linear", "normal_classification")):
            config = _normalize_config({**DEFAULT_FORM_DATA, "model_name": model, "dataset_name": dataset,
                                       "epochs": 1, "num_samples": 100, "num_classes": 20,
                                       "custom_formula": "y = x @ w + b"})
            try:
                with patch.object(plt, "show"), contextlib.redirect_stdout(io.StringIO()):
                    exec(compile(generate_pytorch_code(config), "<exported-model>", "exec"), {})
            finally:
                plt.close("all")


class TrainingRegressionTests(SimpleTestCase):
    def test_jobs_belong_to_their_creator(self):
        from deeplearning.utils import trainer
        with patch.object(trainer.threading.Thread, "start"):
            job_id = trainer.start_training_job(_normalize_config(DEFAULT_FORM_DATA), user_id=1)
        try:
            self.assertIsNone(trainer.get_training_job(job_id, user_id=2))
            self.assertEqual(trainer.get_training_job(job_id, user_id=1)["job_id"], job_id)
        finally:
            trainer.TRAINING_JOBS.pop(job_id, None)

    def test_real_training_finishes(self):
        import time
        from deeplearning.utils import trainer
        config = _normalize_config({**DEFAULT_FORM_DATA, "epochs": 1, "num_samples": 100})
        job_id = trainer.start_training_job(config, user_id=1)
        for _ in range(300):
            job = trainer.get_training_job(job_id, user_id=1)
            if job["status"] in ("finished", "error"):
                break
            time.sleep(.1)
        self.assertEqual(job["status"], "finished", job["message"])
        self.assertEqual(len(job["history"]["epoch"]), 1)
