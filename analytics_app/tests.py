import io
import json
from unittest.mock import patch
from urllib.error import HTTPError, URLError

from django.contrib.auth import get_user_model
from django.test import SimpleTestCase, TestCase, override_settings

from .iching_data import get_hex_by_array
from .zhipu_client import InterpretationError, _normalize_result, _parse_content, _post_json, zhipu_interpret_optional


def completion(content, reason="stop"):
    return {"choices": [{"message": {"content": content}, "finish_reason": reason}]}


VALID = {"translation": "卦辞：恒久，重在持守。", "interpretation": ["每天留出稳定的学习时间。"],
         "answer": "先小步尝试，再根据实际进展调整。", "anecdotes": []}


@override_settings(OPENAI_API_KEY="test-key", ZAI_MODEL="test-model", ZAI_BASE_URL="https://example.invalid/v4/")
class InterpretationTests(SimpleTestCase):
    def interpret(self):
        return zhipu_interpret_optional("如何推进项目？", get_hex_by_array([0, 0, 0, 1, 1, 0]),
                                        get_hex_by_array([0, 1, 1, 1, 0, 0]), [2, 3, 5])

    def test_nested_answer_translation_keeps_labels(self):
        data = {"answer": {**VALID, "translation": {"萃卦卦辞": "亨通。", "恒卦卦辞": "长久。",
                              "萃卦动爻爻辞": {"六二": "诚信有利于祭祀。", "六三": "有所前往。"}}}}
        result = _normalize_result(_parse_content(json.dumps(data, ensure_ascii=False)))
        self.assertIn("萃卦动爻爻辞：六二：诚信", result["translation"])
        self.assertIn("六三：有所前往", result["translation"])
        self.assertEqual(result["interpretation"], VALID["interpretation"])

    def test_fenced_and_surrounded_json(self):
        raw = json.dumps(VALID)
        for value in (raw, "\ufeff" + raw, "```json\n" + raw + "\n```", "解读如下：\n" + raw + "\n供参考。"):
            self.assertEqual(_normalize_result(_parse_content(value))["translation"], VALID["translation"])

    def test_incomplete_outer_json_is_not_repaired(self):
        for raw in ('{"answer": ' + json.dumps(VALID), '{"translation": "尚未完成', "[]", "null", ""):
            with self.subTest(raw=raw), self.assertRaises(InterpretationError):
                _normalize_result(_parse_content(raw))

    def test_reject_multiple_json_objects(self):
        with self.assertRaises(InterpretationError):
            _parse_content(json.dumps(VALID) + json.dumps(VALID))

    def test_normalize_type_variants(self):
        data = {**VALID, "interpretation": {"建议一": "坚持记录。"}, "anecdotes": {"title": None, "content": "文化背景。"}}
        result = _normalize_result(data)
        self.assertEqual(result["interpretation"], ["建议一：坚持记录。"])
        self.assertEqual(result["anecdotes"][0]["title"], "文化背景")
        self.assertTrue(result["disclaimer"])

    def test_missing_required_sections_fail(self):
        for value in ({}, {**VALID, "translation": 4}, {**VALID, "interpretation": [None, 42, {}]}):
            with self.subTest(value=value), self.assertRaises(InterpretationError):
                _normalize_result(value)

    @patch("analytics_app.zhipu_client._post_json")
    def test_truncated_response_retried_with_larger_budget(self, post):
        post.side_effect = [completion('{"answer": {"translation":', "length"), completion(json.dumps(VALID))]
        self.assertEqual(self.interpret()["translation"], VALID["translation"])
        self.assertEqual(post.call_count, 2)
        self.assertEqual(post.call_args.kwargs["api_key"], "test-key")
        payload = post.call_args.args[1]
        self.assertEqual(payload["max_tokens"], 6144)
        self.assertNotIn("reasoning_method", payload)
        user = json.loads(payload["messages"][1]["content"])
        self.assertEqual(len(user["primary"]["moving_lines"]), 3)
        self.assertNotIn("all_lines", user["primary"])

    @patch("analytics_app.zhipu_client._post_json")
    def test_invalid_format_retried_once(self, post):
        post.side_effect = [completion("不是 JSON"), completion(json.dumps({"answer": VALID}))]
        self.assertIn("translation", self.interpret())
        self.assertEqual(post.call_count, 2)

    @patch("analytics_app.zhipu_client._post_json")
    def test_persistent_truncation_has_actionable_private_error(self, post):
        post.return_value = completion('{"translation":"私人问题 secret123', "length")
        result = self.interpret()
        self.assertIn("长度上限", result["error"])
        self.assertNotIn("secret123", result["error"])
        self.assertEqual(post.call_count, 2)

    @patch("analytics_app.zhipu_client._post_json")
    def test_filter_response_not_retried(self, post):
        post.return_value = completion("", "sensitive")
        self.assertIn("error", self.interpret())
        post.assert_called_once()

    @patch("analytics_app.zhipu_client._post_json")
    def test_malformed_provider_envelope(self, post):
        for data in ({}, {"choices": []}, {"choices": [None]}):
            post.return_value = data
            self.assertIn("error", self.interpret())

    @override_settings(OPENAI_API_KEY="")
    @patch("analytics_app.zhipu_client._post_json")
    def test_no_key_never_calls_provider(self, post):
        self.assertIn("OPENAI_API_KEY", self.interpret()["error"])
        post.assert_not_called()

    @patch("analytics_app.zhipu_client.urllib.request.urlopen")
    def test_http_error_does_not_expose_provider_body(self, open_url):
        open_url.side_effect = HTTPError("https://example.invalid", 401, "Unauthorized", {}, io.BytesIO(b"secret body"))
        with self.assertRaisesRegex(InterpretationError, "密钥无效"):
            _post_json("https://example.invalid", {}, api_key="test")

    @patch("analytics_app.zhipu_client.urllib.request.urlopen")
    def test_timeout_has_bounded_single_call(self, open_url):
        open_url.side_effect = URLError("private network details")
        with self.assertRaisesRegex(InterpretationError, "网络不可用"):
            _post_json("https://example.invalid", {}, api_key="test")
        open_url.assert_called_once()


class InterpretationFlowTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = get_user_model().objects.create_user("iching-tester", password="test-password")
        cls.other = get_user_model().objects.create_user("iching-other")

    def setUp(self):
        self.client.force_login(self.user)

    def cast(self):
        return self.client.post("/analytics/iching/cast-ajax/", {"question": "长期学习计划", "method": "coins"}).json()

    @patch("analytics_app.views.zhipu_interpret_optional", return_value=VALID)
    def test_retry_keeps_same_hexagram_and_question(self, interpret):
        cast = self.cast()
        interpret.assert_not_called()
        for _ in range(2):
            response = self.client.post("/analytics/iching/interpret/", {"token": cast["ai_token"]})
            self.assertEqual(response.status_code, 200)
            self.assertEqual(interpret.call_args.args[0], "长期学习计划")
            self.assertEqual(interpret.call_args.args[1]["array"], cast["primary"]["array"])
            self.assertEqual(interpret.call_args.args[3], cast["moving_lines"])
            self.assertIn("01 · 白话译文", response.json()["html"])

    def test_token_cannot_be_changed_or_shared_between_users(self):
        token = self.cast()["ai_token"]
        self.assertEqual(self.client.post("/analytics/iching/interpret/", {"token": token + "x"}).status_code, 400)
        self.client.force_login(self.other)
        self.assertEqual(self.client.post("/analytics/iching/interpret/", {"token": token}).status_code, 400)

    @patch("django.core.signing.time.time")
    def test_expired_token(self, now):
        now.return_value = 10000
        token = self.cast()["ai_token"]
        now.return_value = 13601
        self.assertEqual(self.client.post("/analytics/iching/interpret/", {"token": token}).status_code, 400)

    def test_auth_post_and_csrf_required(self):
        from django.test import Client
        self.assertEqual(self.client.get("/analytics/iching/interpret/").status_code, 405)
        self.client.logout()
        self.assertEqual(self.client.post("/analytics/iching/interpret/").status_code, 302)
        csrf_client = Client(enforce_csrf_checks=True)
        csrf_client.force_login(self.user)
        self.assertEqual(csrf_client.post("/analytics/iching/interpret/").status_code, 403)

    @patch("analytics_app.views.zhipu_interpret_optional", return_value={**VALID, "translation": '<script>alert("x")</script>'})
    def test_ai_html_escapes_content_in_ajax_and_direct_view(self, interpret):
        cast = self.cast()
        html = self.client.post("/analytics/iching/interpret/", {"token": cast["ai_token"]}).json()["html"]
        self.assertNotIn("<script>", html)
        self.assertIn("&lt;script&gt;", html)
        response = self.client.post("/analytics/iching/cast/", {"method": "coins", "use_ai": "1"})
        self.assertContains(response, "&lt;script&gt;")
        self.assertContains(response, "回应你的问题")

    def test_question_length_limit(self):
        for path in ("cast", "cast-ajax"):
            self.assertEqual(self.client.post(f"/analytics/iching/{path}/", {"question": "x" * 1001}).status_code, 400)
