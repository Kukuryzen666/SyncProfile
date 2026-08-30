import json
import os
import sys
import types
import unittest
from unittest.mock import MagicMock

# Mock exteraGram / Android environment modules
android_utils_mock = types.ModuleType("android_utils")
android_utils_mock.log = MagicMock()
android_utils_mock.run_on_ui_thread = lambda fn: fn()
sys.modules["android_utils"] = android_utils_mock

base_plugin_mock = types.ModuleType("base_plugin")
class BasePlugin:
    def __init__(self):
        self.settings = {}
    def get_setting(self, key, default=None):
        return self.settings.get(key, default)
    def set_setting(self, key, val, reload_settings=True):
        self.settings[key] = val
    def hook_method(self, m, hook):
        return MagicMock()
    def unhook_method(self, un):
        pass

class MethodHook:
    def before_hooked_method(self, param): pass
    def after_hooked_method(self, param): pass

class HookStrategy:
    DEFAULT = "DEFAULT"
    CANCEL = "CANCEL"
    MODIFY = "MODIFY"
    MODIFY_FINAL = "MODIFY_FINAL"

class HookResult:
    def __init__(self, strategy=HookStrategy.DEFAULT, **kwargs):
        self.strategy = strategy
        for k, v in kwargs.items():
            setattr(self, k, v)

class AppEvent:
    START = 0
    RESUME = 1
    PAUSE = 2
    STOP = 3

base_plugin_mock.AppEvent = AppEvent
base_plugin_mock.BasePlugin = BasePlugin
base_plugin_mock.MethodHook = MethodHook
base_plugin_mock.HookResult = HookResult
base_plugin_mock.HookStrategy = HookStrategy
base_plugin_mock.MenuItemData = MagicMock()
base_plugin_mock.MenuItemType = MagicMock()
sys.modules["base_plugin"] = base_plugin_mock

hook_utils_mock = types.ModuleType("hook_utils")
hook_utils_mock.find_class = lambda name: None
sys.modules["hook_utils"] = hook_utils_mock

ui_mock = types.ModuleType("ui")
ui_bulletin_mock = types.ModuleType("ui.bulletin")
ui_bulletin_mock.BulletinHelper = MagicMock()
sys.modules["ui"] = ui_mock
sys.modules["ui.bulletin"] = ui_bulletin_mock

ui_settings_mock = types.ModuleType("ui.settings")
def _mock_divider(text=None):
    return ("Divider", {"text": text})
def _mock_header(text=""):
    return ("Header", {"text": text})
def _mock_input(key, text, default="", subtext=None, icon=None, on_change=None):
    return ("Input", {"key": key, "text": text, "default": default, "subtext": subtext, "icon": icon, "on_change": on_change})
def _mock_selector(key, text, default=0, items=None, icon=None, on_change=None):
    return ("Selector", {"key": key, "text": text, "default": default, "items": items, "icon": icon, "on_change": on_change})
def _mock_switch(key, text, default=False, subtext=None, icon=None, on_change=None):
    return ("Switch", {"key": key, "text": text, "default": default, "subtext": subtext, "icon": icon, "on_change": on_change})
def _mock_text(text, subtext=None, icon=None, accent=False, red=False, on_click=None):
    return ("Text", {"text": text, "subtext": subtext, "icon": icon, "accent": accent, "red": red, "on_click": on_click})

ui_settings_mock.Divider = _mock_divider
ui_settings_mock.Header = _mock_header
ui_settings_mock.Input = _mock_input
ui_settings_mock.Selector = _mock_selector
ui_settings_mock.Switch = _mock_switch
ui_settings_mock.Text = _mock_text
sys.modules["ui.settings"] = ui_settings_mock

tgnet_mock = types.ModuleType("org.telegram.tgnet")
class MockTLRPC:
    class TL_peerColor:
        def __init__(self):
            self.color = 0
            self.background_emoji_id = 0
            self.flags = 0

    class TL_emojiStatus:
        def __init__(self):
            self.document_id = 0

    class TL_messageEntityCustomEmoji:
        def __init__(self, offset=0, length=0, document_id=0):
            self.offset = offset
            self.length = length
            self.document_id = document_id

    class TL_messageEntityTextUrl:
        def __init__(self, offset=0, length=0, url=""):
            self.offset = offset
            self.length = length
            self.url = url

    class Message:
        def __init__(self, message="", entities=None):
            self.id = 1
            self.message = message
            self.entities = entities if entities is not None else []

    class TL_updateNewMessage:
        def __init__(self, message=None):
            self.message = message

    class TL_messages_messages:
        def __init__(self, messages=None):
            self.messages = messages if messages is not None else []

    class TL_vector(list):
        def add(self, item):
            self.append(item)
        def size(self):
            return len(self)
        def get(self, idx):
            return self[idx]

tgnet_mock.TLRPC = MockTLRPC
sys.modules["org.telegram.tgnet"] = tgnet_mock

# Mock telegram messenger classes
tg_messenger = types.ModuleType("org.telegram.messenger")
class MockUserConfigInstance:
    def __init__(self, acc_idx=0):
        self.acc_idx = acc_idx
    def getClientUserId(self):
        return 12345
    def isClientActivated(self):
        return True
    def getCurrentUser(self):
        return MockUser(12345)

class MockUserConfig:
    selectedAccount = 0
    MAX_ACCOUNT_COUNT = 4
    _instances = {}

    @classmethod
    def getInstance(cls, acc=0):
        if acc not in cls._instances:
            cls._instances[acc] = MockUserConfigInstance(acc)
        return cls._instances[acc]

class MockSharedConfig:
    animateAvatars = False
    autoplayVideo = False
    autoplayGifs = False
    loopStickers = False
    saveConfig = MagicMock()

tg_messenger.UserConfig = MockUserConfig
tg_messenger.SharedConfig = MockSharedConfig
sys.modules["org.telegram.messenger"] = tg_messenger

# Mock client config classes
ayugram_mock = types.ModuleType("com.radolyn.ayugram")
class MockAyuConfig:
    localPremium = False
    animateAvatars = False
    autoplayVideo = False
    loopAvatars = False
    statusEmojiId = 0
    nameColor = 0
    profileColor = 0
    nameCustomEmojiId = 0
    profileCustomEmojiId = 0
    saveConfig = MagicMock()

ayugram_mock.AyuConfig = MockAyuConfig
sys.modules["com.radolyn.ayugram"] = ayugram_mock

class MockUser:
    def __init__(self, uid=12345):
        self.id = uid
        self.first_name = "Test"
        self.last_name = "User"
        self.photo = None
        self.color = None
        self.profile_color = None
        self.emoji_status = None
        self.premium = False
        self.flags = 0
        self.flags2 = 0

class MockFullUser:
    def __init__(self, uid=12345):
        self.id = uid
        self.user = MockUser(uid)
        self.profile_photo = None
        self.fallback_photo = None
        self.personal_photo = None
        self.color = None
        self.profile_color = None

class MockChat:
    def __init__(self, cid=1234567890, is_channel=True):
        self.id = cid
        self.title = "Test Channel" if is_channel else "Test Group"
        self.broadcast = is_channel
        self.megagroup = not is_channel
        self.photo = None
        self.color = None
        self.profile_color = None
        self.emoji_status = None
        self.level = 0
        self.flags = 0
        self.flags2 = 0

class MockChatFull:
    def __init__(self, cid=1234567890):
        self.id = cid
        self.chat = MockChat(cid)
        self.color = None
        self.profile_color = None
        self.custom_status = None
        self.emoji_status = None
        self.boosts_applied = 0

class MockPhoto:
    def __init__(self, photo_id=987654321, has_video=False, video_sizes=None, flags=0):
        self.photo_id = photo_id
        self.has_video = has_video
        self.video_sizes = video_sizes or []
        self.flags = flags

def load_plugin_module(plugin_filename="sync_ayugram.plugin"):
    import importlib.util
    from importlib.machinery import SourceFileLoader
    file_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", plugin_filename))
    loader = SourceFileLoader(plugin_filename.replace(".", "_"), file_path)
    spec = importlib.util.spec_from_loader(plugin_filename.replace(".", "_"), loader)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.TLRPC = MockTLRPC
    return module

class TestSyncProfileVideoAndLogic(unittest.TestCase):
    def test_safe_int_and_helpers(self):
        module = load_plugin_module()
        
        self.assertEqual(module._safe_int(123), 123)
        self.assertEqual(module._safe_int("456"), 456)
        self.assertEqual(module._safe_int(None, 5), 5)
        self.assertEqual(module._safe_int("invalid", 0), 0)
        
        u = MockUser(999)
        self.assertTrue(module._is_user(u))
        self.assertFalse(module._is_chat(u))

        c = MockChat(123456789)
        self.assertTrue(module._is_chat(c))
        self.assertFalse(module._is_user(c))

    def test_normalize_chat_id(self):
        module = load_plugin_module()

        self.assertEqual(module._normalize_chat_id(1234567890), 1234567890)
        self.assertEqual(module._normalize_chat_id("1234567890"), 1234567890)
        self.assertEqual(module._normalize_chat_id(-1001234567890), 1234567890)
        self.assertEqual(module._normalize_chat_id("-1001234567890"), 1234567890)
        self.assertEqual(module._normalize_chat_id(-987654), 987654)
        self.assertEqual(module._normalize_chat_id(0), 0)
        self.assertEqual(module._normalize_chat_id(None), 0)
        self.assertEqual(module._normalize_chat_id("invalid"), 0)

    def test_static_photo_not_marked_as_video(self):
        ph = MockPhoto(photo_id=123456789, has_video=False, video_sizes=[], flags=0)
        v_sizes = getattr(ph, "video_sizes", None)
        has_v = bool(
            getattr(ph, "has_video", False)
            or (v_sizes and (hasattr(v_sizes, "isEmpty") and not v_sizes.isEmpty() or len(v_sizes) > 0))
            or ((int(getattr(ph, "flags", 0) or 0) & 1) != 0)
        )
        self.assertFalse(has_v)

    def test_real_video_avatar_detected(self):
        ph1 = MockPhoto(photo_id=123456789, has_video=True, video_sizes=[], flags=0)
        v_sizes1 = getattr(ph1, "video_sizes", None)
        has_v1 = bool(
            getattr(ph1, "has_video", False)
            or (v_sizes1 and (hasattr(v_sizes1, "isEmpty") and not v_sizes1.isEmpty() or len(v_sizes1) > 0))
            or ((int(getattr(ph1, "flags", 0) or 0) & 1) != 0)
        )
        self.assertTrue(has_v1)

        ph2 = MockPhoto(photo_id=123456789, has_video=False, video_sizes=["video_size_mock"], flags=0)
        v_sizes2 = getattr(ph2, "video_sizes", None)
        has_v2 = bool(
            getattr(ph2, "has_video", False)
            or (v_sizes2 and (hasattr(v_sizes2, "isEmpty") and not v_sizes2.isEmpty() or len(v_sizes2) > 0))
            or ((int(getattr(ph2, "flags", 0) or 0) & 1) != 0)
        )
        self.assertTrue(has_v2)

        ph3 = MockPhoto(photo_id=123456789, has_video=False, video_sizes=[], flags=1)
        v_sizes3 = getattr(ph3, "video_sizes", None)
        has_v3 = bool(
            getattr(ph3, "has_video", False)
            or (v_sizes3 and (hasattr(v_sizes3, "isEmpty") and not v_sizes3.isEmpty() or len(v_sizes3) > 0))
            or ((int(getattr(ph3, "flags", 0) or 0) & 1) != 0)
        )
        self.assertTrue(has_v3)

    def test_patch_user_tl_object(self):
        module = load_plugin_module()

        plugin = module.Plugin()
        user = MockUser(uid=112233)
        user.photo = MockPhoto(photo_id=777)

        plugin._profiles_cache[112233] = {
            "user_id": 112233,
            "name_color": 2,
            "name_bg_emoji_id": 0,
            "profile_color": 3,
            "profile_bg_emoji_id": 0,
            "emoji_status_id": 0,
            "premium": True
        }
        plugin._update_snapshot()

        res = plugin._patch_user_tl_object(user)
        self.assertTrue(res)
        self.assertEqual(user.color.color, 2)
        self.assertEqual(user.profile_color.color, 3)
        self.assertTrue(user.premium)

    def test_patch_chat_and_channel_tl_object(self):
        module = load_plugin_module()

        plugin = module.Plugin()
        chat = MockChat(cid=1234567890, is_channel=True)
        chat.photo = MockPhoto(photo_id=888, has_video=True)

        plugin._chats_cache[1234567890] = {
            "chat_id": 1234567890,
            "name_color": 10,
            "name_bg_emoji_id": 5215441234567890123,
            "profile_color": 2,
            "profile_bg_emoji_id": 5215441234567890123,
            "emoji_status_id": 5382148123456789012,
            "boost_level": 10
        }
        plugin._update_snapshot()

        res = plugin._patch_chat_tl_object(chat)
        self.assertTrue(res)
        self.assertEqual(chat.color.color, 10)
        self.assertEqual(chat.color.background_emoji_id, 5215441234567890123)
        self.assertEqual(chat.profile_color.color, 2)
        self.assertEqual(chat.emoji_status.document_id, 5382148123456789012)
        self.assertEqual(chat.level, 10)
        self.assertTrue(chat.photo.has_video)

    def test_patch_full_chat_tl_object(self):
        module = load_plugin_module()

        plugin = module.Plugin()
        full_chat = MockChatFull(cid=1234567890)

        plugin._chats_cache[1234567890] = {
            "chat_id": 1234567890,
            "name_color": 10,
            "name_bg_emoji_id": 0,
            "profile_color": 2,
            "profile_bg_emoji_id": 0,
            "emoji_status_id": 5382148123456789012,
            "boost_level": 10
        }
        plugin._update_snapshot()

        res = plugin._patch_full_chat_tl_object(full_chat, 1234567890)
        self.assertTrue(res)
        self.assertEqual(full_chat.profile_color.color, 2)
        self.assertEqual(full_chat.custom_status.document_id, 5382148123456789012)
        self.assertEqual(full_chat.boosts_applied, 10)

    def test_cache_serialization_and_deserialization(self):
        module = load_plugin_module()
        plugin = module.Plugin()

        plugin._profiles_cache[111] = {"user_id": 111, "name_color": 1}
        plugin._chats_cache[222] = {"chat_id": 222, "name_color": 2}
        plugin._cache_dirty = True
        plugin._update_snapshot()

        # Save to disk / settings
        plugin._save_local_profiles_cache(force=True)

        # Clear and reload
        plugin._profiles_cache.clear()
        plugin._chats_cache.clear()
        plugin._update_snapshot()
        self.assertEqual(len(plugin._profiles_cache), 0)
        self.assertEqual(len(plugin._chats_cache), 0)

        plugin._load_local_profiles_cache()
        self.assertIn(111, plugin._profiles_cache)
        self.assertIn(222, plugin._chats_cache)
        self.assertEqual(plugin._profiles_cache[111]["name_color"], 1)
        self.assertEqual(plugin._chats_cache[222]["name_color"], 2)

        # Clean up test cache file if created
        if os.path.exists("sync_profiles_cache.json"):
            try:
                os.remove("sync_profiles_cache.json")
            except Exception:
                pass

    def test_legacy_cache_migration(self):
        if os.path.exists("sync_profiles_cache.json"):
            try:
                os.remove("sync_profiles_cache.json")
            except Exception:
                pass
        module = load_plugin_module()
        plugin = module.Plugin()

        # Simulate legacy cache format: flat {uid_str: profile_data}
        legacy_data = {
            "999888": {"user_id": 999888, "name_color": 3, "premium": True}
        }
        plugin.set_setting("_local_profiles_json", json.dumps(legacy_data))

        plugin._load_local_profiles_cache()
        self.assertIn(999888, plugin._profiles_cache)
        self.assertEqual(plugin._profiles_cache[999888]["name_color"], 3)

    def test_extract_message_and_emoji_ids(self):
        module = load_plugin_module()
        plugin = module.Plugin()

        class MockTL_doc:
            def __init__(self, doc_id): self.id = doc_id
        class MockTL_media:
            def __init__(self, doc_id): self.document = MockTL_doc(doc_id)
        class MockTL_entity:
            def __init__(self, doc_id): self.document_id = doc_id
        class MockMsg:
            def __init__(self, doc_ids=None, media_doc_id=None):
                self.id = 42
                self.entities = [MockTL_entity(d) for d in (doc_ids or [])]
                self.media = MockTL_media(media_doc_id) if media_doc_id else None
        class MockMO:
            def __init__(self, msg, text=""):
                self.messageOwner = msg
                self.messageText = text
        class MockCell:
            def __init__(self, mo): self._mo = mo
            def getMessageObject(self): return self._mo
        class MockFrag:
            def __init__(self, mo): self.selectedObject = mo
        class MockSpan:
            def __init__(self, doc_id): self.documentId = doc_id
        class MockSpannable:
            def __init__(self, text, spans):
                self.text = text
                self._spans = spans
            def length(self): return len(self.text)
            def getSpans(self, s, e, cls): return self._spans

        mo1 = MockMO(MockMsg([5215441234567890123, 5382148123456789012]))
        cell1 = MockCell(mo1)
        frag1 = MockFrag(mo1)

        # Test resolution from diverse inputs
        self.assertIsNotNone(plugin._extract_message_from_menu_args(mo1))
        self.assertIsNotNone(plugin._extract_message_from_menu_args(cell=cell1))
        self.assertIsNotNone(plugin._extract_message_from_menu_args(frag1))
        self.assertIsNotNone(plugin._extract_message_from_menu_args({"msg": mo1}))
        self.assertIsNotNone(plugin._extract_message_from_menu_args({"fragment": frag1}))

        # Test emoji ID extraction from entities
        ids1 = plugin._extract_custom_emoji_ids(mo1)
        self.assertEqual(ids1, [5215441234567890123, 5382148123456789012])

        # Test emoji ID extraction from Spannable text
        mo2 = MockMO(MockMsg(), text=MockSpannable("test", [MockSpan(999888777)]))
        ids2 = plugin._extract_custom_emoji_ids(mo2)
        self.assertEqual(ids2, [999888777])

        # Test emoji ID extraction from media sticker
        mo3 = MockMO(MockMsg(media_doc_id=777666555))
        ids3 = plugin._extract_custom_emoji_ids(mo3)
        self.assertEqual(ids3, [777666555])

        # Test emoji ID extraction from captionEntities
        class MockCaptionMsg:
            def __init__(self, doc_ids):
                self.id = 55
                self.captionEntities = [MockTL_entity(d) for d in doc_ids]
        mo4 = MockMO(MockCaptionMsg([111222333444]))
        ids4 = plugin._extract_custom_emoji_ids(mo4)
        self.assertEqual(ids4, [111222333444])

        # Test emoji ID extraction from reactions
        class MockReaction:
            def __init__(self, doc_id): self.document_id = doc_id
        class MockReactionResult:
            def __init__(self, doc_id): self.reaction = MockReaction(doc_id)
        class MockReactionsHolder:
            def __init__(self, doc_ids): self.results = [MockReactionResult(d) for d in doc_ids]
        class MockReactionMsg:
            def __init__(self, doc_ids):
                self.id = 66
                self.reactions = MockReactionsHolder(doc_ids)
        mo5 = MockMO(MockReactionMsg([888999000111]))
        ids5 = plugin._extract_custom_emoji_ids(mo5)
        self.assertEqual(ids5, [888999000111])

        # Test fallback to tracked last selected message
        plugin._last_selected_message = mo1
        self.assertEqual(plugin._extract_message_from_menu_args(), mo1)
        self.assertEqual(plugin._extract_message_from_menu_args(None), mo1)

        # Test on_copy_emoji_id_click invocation
        plugin._on_copy_emoji_id_click(mo1)
        plugin._on_copy_emoji_id_click(cell=cell1)
        plugin._on_copy_emoji_id_click()  # via _last_selected_message

    def test_parse_items_map(self):
        module = load_plugin_module()
        plugin = module.Plugin()

        # 1. Test parsing chats as list of dicts (standard SQLite row output)
        chats_list = [
            {"chat_id": 123456789, "name_color": 5, "profile_color": 3},
            {"id": -100987654321, "name_color": 2, "profile_color": 1}
        ]
        parsed_chats = plugin._parse_items_map(chats_list, is_chat=True)
        self.assertIn(123456789, parsed_chats)
        self.assertIn(987654321, parsed_chats)
        self.assertEqual(parsed_chats[123456789]["name_color"], 5)
        self.assertEqual(parsed_chats[987654321]["name_color"], 2)

        # 2. Test parsing chats as dict with string keys
        chats_dict = {
            "-10011223344": {"name_color": 4, "profile_color": 2},
            "55667788": {"chat_id": 55667788, "name_color": 7}
        }
        parsed_chats_dict = plugin._parse_items_map(chats_dict, is_chat=True)
        self.assertIn(11223344, parsed_chats_dict)
        self.assertIn(55667788, parsed_chats_dict)
        self.assertEqual(parsed_chats_dict[11223344]["name_color"], 4)

        # 3. Test parsing profiles as list
        profs_list = [{"user_id": 111, "name_color": 1}, {"id": 222, "name_color": 2}]
        parsed_profs = plugin._parse_items_map(profs_list, is_chat=False)
        self.assertIn(111, parsed_profs)
        self.assertIn(222, parsed_profs)

    def test_create_settings_has_switches(self):
        for mod_file in ["sync_ayugram.plugin", "sync_exteragram.plugin"]:
            module = load_plugin_module(mod_file)
            plugin = module.Plugin()
            items = plugin.create_settings()
            self.assertIsInstance(items, list)
            self.assertGreater(len(items), 5)
            
            keys = [item[1].get("key") for item in items if isinstance(item, tuple) and item[0] in ("Switch", "Selector", "Input")]
            self.assertIn("enable_sync", keys)
            self.assertIn("auto_sync_interval", keys)

    def test_ayugram_client_detection(self):
        module = load_plugin_module()
        plugin = module.Plugin()
        self.assertTrue(plugin._is_ayugram())

        # Simulate exteraGram by removing com.radolyn.ayugram
        old_ayugram = sys.modules.pop("com.radolyn.ayugram", None)
        try:
            self.assertFalse(module._is_ayugram())
            self.assertFalse(plugin._is_ayugram())
        finally:
            if old_ayugram:
                sys.modules["com.radolyn.ayugram"] = old_ayugram

    def test_ayugram_own_account_sets_premium(self):
        module = load_plugin_module()
        plugin = module.Plugin()
        
        # Mark uid 555 as an own account
        plugin._own_uids_cache = {555}
        plugin._profiles_cache[555] = {
            "user_id": 555,
            "name_color": 1,
            "premium": True
        }
        plugin._update_snapshot()

        # Own user on AyuGram without official premium gets local premium from SyncProfile
        user_own = MockUser(uid=555)
        user_own.premium = False
        
        plugin._patch_user_tl_object(user_own)
        # On AyuGram, own account gets user.premium=True so video avatars & emoji status render properly
        self.assertTrue(user_own.premium)
        self.assertEqual(user_own.color.color, 1)

        # Other user on AyuGram
        plugin._profiles_cache[777] = {
            "user_id": 777,
            "name_color": 2,
            "premium": True
        }
        plugin._update_snapshot()
        user_other = MockUser(uid=777)
        user_other.premium = False

        plugin._patch_user_tl_object(user_other)
        # Other user gets premium=True for visual rendering
        self.assertTrue(user_other.premium)
        self.assertEqual(user_other.color.color, 2)

    def test_exteragram_own_account_sets_premium(self):
        module = load_plugin_module("sync_exteragram.plugin")
        plugin = module.Plugin()

        old_ayugram = sys.modules.pop("com.radolyn.ayugram", None)
        try:
            # Mark uid 555 as an own account on exteraGram
            plugin._own_uids_cache = {555}
            plugin._profiles_cache[555] = {
                "user_id": 555,
                "name_color": 3,
                "premium": True
            }
            plugin._update_snapshot()

            user_own = MockUser(uid=555)
            user_own.premium = False

            plugin._patch_user_tl_object(user_own)
            # On exteraGram, own account gets premium=True
            self.assertTrue(user_own.premium)
            self.assertEqual(user_own.color.color, 3)
        finally:
            if old_ayugram:
                sys.modules["com.radolyn.ayugram"] = old_ayugram

    def test_ayugram_ensure_local_premium(self):
        module = load_plugin_module("sync_ayugram.plugin")
        plugin = module.Plugin()
        
        MockAyuConfig.localPremium = False
        plugin._ensure_local_premium()
        self.assertTrue(MockAyuConfig.localPremium)
        MockAyuConfig.saveConfig.assert_called()

    def test_patch_user_flags_and_idempotency(self):
        module = load_plugin_module("sync_ayugram.plugin")
        plugin = module.Plugin()

        plugin._profiles_cache[3344] = {
            "user_id": 3344,
            "name_color": 4,
            "name_bg_emoji_id": 111222,
            "profile_color": 5,
            "profile_bg_emoji_id": 333444,
            "emoji_status_id": 555666,
            "premium": True
        }
        plugin._update_snapshot()

        user = MockUser(uid=3344)
        res1 = plugin._patch_user_tl_object(user)
        self.assertTrue(res1)
        self.assertTrue(user.flags & 0x40000000)  # FLAG_EMOJI_STATUS (flags.30)
        self.assertTrue(user.flags2 & 1)          # FLAG2_EMOJI_STATUS (flags2.0)
        self.assertTrue(user.flags2 & 256)        # FLAG2_COLOR
        self.assertTrue(user.flags2 & 512)        # FLAG2_PROFILE_COLOR
        self.assertTrue(user.flags & 0x10000000)  # FLAG_PREMIUM

        # Second call: must be idempotent and preserve exact objects/flags
        prev_color = user.color
        prev_prc = user.profile_color
        prev_st = user.emoji_status
        res2 = plugin._patch_user_tl_object(user)
        self.assertTrue(res2)
        self.assertIs(user.color, prev_color)
        self.assertIs(user.profile_color, prev_prc)
        self.assertIs(user.emoji_status, prev_st)

    def test_patch_full_user_tl_object_emoji_status(self):
        module = load_plugin_module("sync_ayugram.plugin")
        plugin = module.Plugin()

        plugin._profiles_cache[8899] = {
            "user_id": 8899,
            "name_color": 2,
            "name_bg_emoji_id": 0,
            "profile_color": 3,
            "profile_bg_emoji_id": 0,
            "emoji_status_id": 998877,
            "premium": True
        }
        plugin._update_snapshot()

        full_user = MockFullUser(uid=8899)
        res = plugin._patch_full_user_tl_object(full_user, 8899)
        self.assertTrue(res)
        self.assertEqual(full_user.profile_color.color, 3)
        self.assertEqual(full_user.custom_status.document_id, 998877)
        self.assertEqual(full_user.emoji_status.document_id, 998877)
        self.assertTrue(full_user.flags & 0x80000)  # FLAG_CUSTOM_STATUS (1 << 19)
        self.assertEqual(full_user.user.emoji_status.document_id, 998877)

    def test_video_avatar_normalized_for_regular_user(self):
        module = load_plugin_module("sync_ayugram.plugin")
        plugin = module.Plugin()

        # Regular user not in SyncProfile database
        regular_user = MockUser(uid=123456)
        regular_user.photo = MockPhoto(photo_id=555, has_video=False, video_sizes=["mock_video_size"], flags=0)

        res = plugin._patch_user_tl_object(regular_user)
        # Should return False (not in SyncProfile), but photo should be normalized to has_video=True
        self.assertFalse(res)
        self.assertTrue(regular_user.photo.has_video)
        self.assertEqual(regular_user.photo.flags & 1, 1)

    def test_ensure_local_premium_enables_animated_avatars(self):
        module = load_plugin_module("sync_ayugram.plugin")
        plugin = module.Plugin()

        MockAyuConfig.localPremium = False
        MockAyuConfig.animateAvatars = False
        MockAyuConfig.autoplayVideo = False
        MockAyuConfig.loopAvatars = False

        plugin._ensure_local_premium()
        self.assertTrue(MockAyuConfig.localPremium)
        self.assertTrue(MockAyuConfig.animateAvatars)
        self.assertTrue(MockAyuConfig.autoplayVideo)
        self.assertTrue(MockAyuConfig.loopAvatars)

    def test_ensure_local_premium_extera_and_koto(self):
        module = load_plugin_module("sync_exteragram.plugin")
        plugin = module.Plugin()

        class MockExteraConfig:
            localPremium = False
            saveConfig = MagicMock()
        class MockKotoConfig:
            localPremium = False
            saveConfig = MagicMock()

        if "org.telegram.messenger" not in sys.modules:
            sys.modules["org.telegram.messenger"] = types.ModuleType("org.telegram.messenger")

        tg_messenger = sys.modules["org.telegram.messenger"]
        tg_messenger.ExteraConfig = MockExteraConfig
        tg_messenger.KotoConfig = MockKotoConfig
        try:
            plugin._ensure_local_premium()
            self.assertTrue(MockExteraConfig.localPremium)
            MockExteraConfig.saveConfig.assert_called()
            self.assertTrue(MockKotoConfig.localPremium)
            MockKotoConfig.saveConfig.assert_called()
        finally:
            if hasattr(tg_messenger, "ExteraConfig"):
                delattr(tg_messenger, "ExteraConfig")
            if hasattr(tg_messenger, "KotoConfig"):
                delattr(tg_messenger, "KotoConfig")

    def test_extract_emoji_doc_id_from_url(self):
        module = load_plugin_module("sync_exteragram.plugin")
        self.assertEqual(module._extract_emoji_doc_id_from_url("tg://emoji?id=5299025466055734222"), 5299025466055734222)
        self.assertEqual(module._extract_emoji_doc_id_from_url("tg://emoji?document_id=5299025466055734222"), 5299025466055734222)
        self.assertEqual(module._extract_emoji_doc_id_from_url("tg://emoji?id=5299025466055734222&fallback=smile"), 5299025466055734222)
        self.assertEqual(module._extract_emoji_doc_id_from_url("tg://custom-emoji?id=5299025466055734222"), 5299025466055734222)
        self.assertEqual(module._extract_emoji_doc_id_from_url("https://t.me/emoji/5299025466055734222"), 5299025466055734222)
        self.assertIsNone(module._extract_emoji_doc_id_from_url("https://google.com"))
        self.assertIsNone(module._extract_emoji_doc_id_from_url(""))
        self.assertIsNone(module._extract_emoji_doc_id_from_url(None))

    def test_convert_custom_emojis_to_text_urls(self):
        module = load_plugin_module("sync_exteragram.plugin")
        orig_emoji = MockTLRPC.TL_messageEntityCustomEmoji(offset=0, length=2, document_id=5299025466055734222)
        entities = [orig_emoji]

        converted = module._convert_custom_emojis_to_text_urls(entities)
        self.assertEqual(len(converted), 1)
        self.assertIsInstance(converted[0], MockTLRPC.TL_messageEntityTextUrl)
        self.assertEqual(converted[0].url, "tg://emoji?id=5299025466055734222")
        self.assertEqual(converted[0].offset, 0)
        self.assertEqual(converted[0].length, 2)

    def test_convert_text_urls_to_custom_emojis(self):
        module = load_plugin_module("sync_exteragram.plugin")
        text_url = MockTLRPC.TL_messageEntityTextUrl(offset=3, length=2, url="tg://emoji?id=5299025466055734222")
        entities = [text_url]

        converted = module._convert_text_urls_to_custom_emojis(entities)
        self.assertEqual(len(converted), 1)
        self.assertIsInstance(converted[0], MockTLRPC.TL_messageEntityCustomEmoji)
        self.assertEqual(converted[0].document_id, 5299025466055734222)
        self.assertEqual(converted[0].offset, 3)
        self.assertEqual(converted[0].length, 2)

    def test_exteragram_on_send_message_hook(self):
        module = load_plugin_module("sync_exteragram.plugin")
        plugin = module.Plugin()

        # None params
        res = plugin.on_send_message_hook(0, None)
        self.assertEqual(res.strategy, module.HookStrategy.DEFAULT)

        # Message params with custom emoji
        class MockSendParams:
            def __init__(self, message, entities):
                self.message = message
                self.entities = entities

        params = MockSendParams("Hello", [MockTLRPC.TL_messageEntityCustomEmoji(0, 2, 777888999)])
        res2 = plugin.on_send_message_hook(0, params)
        self.assertEqual(res2.strategy, module.HookStrategy.MODIFY)
        self.assertIsInstance(params.entities[0], MockTLRPC.TL_messageEntityTextUrl)
        self.assertEqual(params.entities[0].url, "tg://emoji?id=777888999")

    def test_exteragram_on_send_message_hook_converts_emojis(self):
        module = load_plugin_module("sync_exteragram.plugin")
        plugin = module.Plugin()

        class MockParams:
            def __init__(self, entities):
                self.entities = entities

        params = MockParams([MockTLRPC.TL_messageEntityCustomEmoji(0, 2, 1122334455)])
        res = plugin.on_send_message_hook(0, params)
        self.assertEqual(res.strategy, module.HookStrategy.MODIFY)
        self.assertIsInstance(params.entities[0], MockTLRPC.TL_messageEntityTextUrl)
        self.assertEqual(params.entities[0].url, "tg://emoji?id=1122334455")

    def test_exteragram_convert_emojis_to_and_from_urls(self):
        module = load_plugin_module("sync_exteragram.plugin")

        # Custom emoji -> Text url
        ents = [MockTLRPC.TL_messageEntityCustomEmoji(0, 4, 999111222)]
        conv_urls = module._convert_custom_emojis_to_text_urls(ents)
        self.assertIsInstance(conv_urls[0], MockTLRPC.TL_messageEntityTextUrl)
        self.assertEqual(conv_urls[0].url, "tg://emoji?id=999111222")

        # Text url -> Custom emoji
        conv_emojis = module._convert_text_urls_to_custom_emojis(conv_urls)
        self.assertIsInstance(conv_emojis[0], MockTLRPC.TL_messageEntityCustomEmoji)
        self.assertEqual(conv_emojis[0].document_id, 999111222)

    def test_exteragram_settings_has_local_premium_switch(self):
        module = load_plugin_module("sync_exteragram.plugin")
        plugin = module.Plugin()
        items = plugin.create_settings()

        keys = [item[1].get("key") for item in items if isinstance(item, tuple) and item[0] == "Switch"]
        self.assertIn("extera_local_premium", keys)

    def test_clear_cache_button_at_top_and_no_full_download(self):
        for mod_file in ("sync_ayugram.plugin", "sync_exteragram.plugin"):
            module = load_plugin_module(mod_file)
            plugin = module.Plugin()
            items = plugin.create_settings()

            texts = [item[1].get("text", "") for item in items if isinstance(item, tuple) and item[0] == "Text"]
            # Verify clear cache is present in actions
            self.assertTrue(any("Очистить локальный кэш" in t for t in texts))
            # Verify full database download is removed
            self.assertFalse(any("Полное скачивание базы" in t for t in texts))

    def test_clear_cache_action(self):
        for mod_file in ("sync_ayugram.plugin", "sync_exteragram.plugin"):
            module = load_plugin_module(mod_file)
            plugin = module.Plugin()
            plugin._profiles_cache[999888] = {"name_color": 3}
            plugin._chats_cache[67890] = {"name_color": 2}
            plugin.set_setting("_last_sync_timestamp", 123456789)
            plugin._update_snapshot()

            plugin._clear_cache_action()
            # Non-own user cache is cleared
            self.assertNotIn(999888, plugin._profiles_cache)
            self.assertEqual(len(plugin._chats_cache), 0)
            self.assertEqual(plugin.get_setting("_last_sync_timestamp", 0), 0)

    def test_sync_local_ayuconfig_applies_status_and_avatar_flags(self):
        module = load_plugin_module("sync_ayugram.plugin")
        plugin = module.Plugin()

        MockAyuConfig.statusEmojiId = 0
        MockAyuConfig.animateAvatars = False
        MockAyuConfig.autoplayVideo = False

        plugin.set_setting("slot_0_emoji_status_id", "543210987654321")
        plugin.set_setting("slot_0_name_color", 3)
        plugin.set_setting("slot_0_profile_color", 5)

        plugin._sync_local_ayuconfig(0)
        self.assertEqual(MockAyuConfig.statusEmojiId, 543210987654321)
        self.assertEqual(MockAyuConfig.nameColor, 3)
        self.assertEqual(MockAyuConfig.profileColor, 5)
        self.assertTrue(MockAyuConfig.animateAvatars)
        self.assertTrue(MockAyuConfig.autoplayVideo)

    def test_chat_emoji_status_and_flags(self):
        module = load_plugin_module("sync_ayugram.plugin")
        plugin = module.Plugin()

        chat = MockChat(cid=778899, is_channel=True)
        plugin._chats_cache[778899] = {
            "chat_id": 778899,
            "emoji_status_id": 9988776655,
            "name_color": 1,
            "profile_color": 2,
        }
        plugin._update_snapshot()

        res = plugin._patch_chat_tl_object(chat)
        self.assertTrue(res)
        self.assertEqual(chat.emoji_status.document_id, 9988776655)
        self.assertTrue(chat.flags & 512)    # flags.9
        self.assertTrue(chat.flags2 & 1)     # flags2.0
        self.assertTrue(chat.flags2 & 1024)  # flags2.10

    def test_hot_path_set_caching_and_invalidation(self):
        for mod_file in ("sync_exteragram.plugin", "sync_ayugram.plugin"):
            module = load_plugin_module(mod_file)
            plugin = module.Plugin()

            tracked_u = MockUser(uid=111222)
            untracked_u = MockUser(uid=333444)

            plugin._profiles_cache[111222] = {
                "user_id": 111222,
                "name_color": 3,
                "profile_color": 4,
                "emoji_status_id": 55555,
                "premium": True
            }
            plugin._update_snapshot()

            # First patch call sets properties
            self.assertTrue(plugin._patch_user_tl_object(tracked_u))
            self.assertEqual(tracked_u.color.color, 3)
            self.assertEqual(tracked_u.profile_color.color, 4)
            self.assertEqual(tracked_u.emoji_status.document_id, 55555)
            self.assertTrue(tracked_u.premium)
            self.assertFalse(plugin._patch_user_tl_object(untracked_u))

            # Simulate Telegram recreating the Java TLRPC.User object from SQLite / MTProto (e.g. after 10 min idle)
            fresh_u = MockUser(uid=111222)
            self.assertIsNone(fresh_u.color)
            self.assertIsNone(fresh_u.emoji_status)
            self.assertFalse(fresh_u.premium)

            # Patching fresh_u MUST succeed and apply color, emoji status, and premium!
            self.assertTrue(plugin._patch_user_tl_object(fresh_u))
            self.assertIsNotNone(fresh_u.color)
            self.assertEqual(fresh_u.color.color, 3)
            self.assertIsNotNone(fresh_u.emoji_status)
            self.assertEqual(fresh_u.emoji_status.document_id, 55555)
            self.assertTrue(fresh_u.premium)

            # Chats: verify fresh instance patching
            plugin._chats_cache[555666] = {
                "chat_id": 555666,
                "name_color": 1,
                "profile_color": 2,
                "emoji_status_id": 77777,
            }
            plugin._update_snapshot()
            tracked_c = MockChat(cid=555666)
            self.assertTrue(plugin._patch_chat_tl_object(tracked_c))
            self.assertEqual(tracked_c.color.color, 1)
            self.assertEqual(tracked_c.profile_color.color, 2)
            self.assertEqual(tracked_c.emoji_status.document_id, 77777)

            # Fresh chat instance
            fresh_c = MockChat(cid=555666)
            self.assertTrue(plugin._patch_chat_tl_object(fresh_c))
            self.assertEqual(fresh_c.color.color, 1)

    def test_auto_sync_interval_helper(self):
        for fname in ["sync_ayugram.plugin", "sync_exteragram.plugin"]:
            module = load_plugin_module(fname)
            plugin = module.Plugin()

            # Default index 1 -> 120s
            plugin.set_setting("auto_sync_interval", 1)
            self.assertEqual(plugin._get_sync_interval_seconds(), 120)

            # Index 0 -> 60s
            plugin.set_setting("auto_sync_interval", 0)
            self.assertEqual(plugin._get_sync_interval_seconds(), 60)

            # Index 2 -> 300s
            plugin.set_setting("auto_sync_interval", 2)
            self.assertEqual(plugin._get_sync_interval_seconds(), 300)

            # Index 3 -> 600s
            plugin.set_setting("auto_sync_interval", 3)
            self.assertEqual(plugin._get_sync_interval_seconds(), 600)

            # Index 4 -> 900s
            plugin.set_setting("auto_sync_interval", 4)
            self.assertEqual(plugin._get_sync_interval_seconds(), 900)

            # Out of bounds -> fallback 120s
            plugin.set_setting("auto_sync_interval", 99)
            self.assertEqual(plugin._get_sync_interval_seconds(), 120)

    def test_clear_cache_action(self):
        for fname in ["sync_ayugram.plugin", "sync_exteragram.plugin"]:
            module = load_plugin_module(fname)
            plugin = module.Plugin()

            # Mock sync_database to prevent real network calls
            sync_db_called = []
            plugin._sync_database = lambda show_bulletin=False, force_clean=True: sync_db_called.append((show_bulletin, force_clean))

            plugin._profiles_cache[99999] = {"user_id": 99999, "name_color": 3}
            plugin._chats_cache[88888] = {"chat_id": 88888, "name_color": 4}
            plugin.set_setting("_last_sync_timestamp", 12345678)
            plugin._update_snapshot()

            plugin._clear_cache_action()

            # Verify timestamp was reset
            self.assertEqual(plugin.get_setting("_last_sync_timestamp"), 0)
            # Verify foreign profiles were cleared from cache
            self.assertNotIn(99999, plugin._profiles_cache)
            self.assertNotIn(88888, plugin._chats_cache)
            # Verify full database fetch was triggered with force_clean=True
            self.assertTrue(len(sync_db_called) > 0)
            self.assertTrue(sync_db_called[0][1])

    def test_on_app_event_resume(self):
        for fname in ["sync_ayugram.plugin", "sync_exteragram.plugin"]:
            module = load_plugin_module(fname)
            plugin = module.Plugin()

            delta_sync_called = []
            plugin.sync_delta_updates_from_server = lambda show_bulletin=False: delta_sync_called.append(show_bulletin)

            # 1. Last sync timestamp was recent -> no sync needed
            import time
            plugin.set_setting("_last_sync_timestamp", int(time.time()))
            plugin.set_setting("auto_sync_interval", 1)  # 120s
            plugin.on_app_event(module.AppEvent.RESUME)
            self.assertEqual(len(delta_sync_called), 0)

            # 2. Last sync timestamp was 15 minutes ago (expired) -> triggers sync
            plugin.set_setting("_last_sync_timestamp", int(time.time()) - 900)
            plugin.on_app_event(module.AppEvent.RESUME)
            self.assertEqual(len(delta_sync_called), 1)

    def test_ayugram_video_avatar_hooks_registered(self):
        class MockParamType:
            def __init__(self, name):
                self._name = name
            def getName(self):
                return self._name

        class MockJavaMethod:
            def __init__(self, name):
                self._name = name
                self._param_types = [MockParamType("long")] if name in ("getUser", "getChat", "getUserFull", "getChatFull") else [MockParamType("org.telegram.tgnet.TLRPC$User")]
            def getName(self):
                return self._name
            def getParameterTypes(self):
                return self._param_types
            def setAccessible(self, val):
                pass

        class MockJavaClass:
            def __init__(self, methods):
                self._methods = [MockJavaMethod(m) for m in methods]
            def getMethods(self):
                return self._methods

        module = load_plugin_module("sync_ayugram.plugin")
        plugin = module.Plugin()

        fake_classes = {
            "org.telegram.messenger.MessagesController": MockJavaClass(["getUser", "getChat", "getUserFull", "getChatFull", "putUser", "putChat"]),
        }

        orig_find_class = module.find_class
        try:
            module.find_class = lambda name: fake_classes.get(name)
            plugin._register_xposed_hooks()
            # Verify MessagesController hooks were registered
            self.assertGreater(len(plugin._xposed_unhooks), 0)
        finally:
            module.find_class = orig_find_class

    def test_exteragram_fast_emoji_doc_id_extraction(self):
        module = load_plugin_module("sync_exteragram.plugin")
        extract_fn = module._extract_emoji_doc_id_from_url

        # Test valid emoji urls
        self.assertEqual(extract_fn("tg://emoji?id=543219876"), 543219876)
        self.assertEqual(extract_fn("tg://custom-emoji?id=12345&foo=bar"), 12345)
        self.assertEqual(extract_fn("https://t.me/emoji/99887766?test=1"), 99887766)
        self.assertEqual(extract_fn("t.me/emoji/11223344"), 11223344)

        # Test non-emoji urls (must quickly return None without errors)
        self.assertIsNone(extract_fn("https://google.com"))
        self.assertIsNone(extract_fn("https://t.me/durov"))
        self.assertIsNone(extract_fn(""))
        self.assertIsNone(extract_fn(None))

    def test_exteragram_message_entities_patching_and_sp_flag(self):
        module = load_plugin_module("sync_exteragram.plugin")

        class MockEntityTextUrl:
            def __init__(self, url, offset=0, length=2):
                self.url = url
                self.offset = offset
                self.length = length

        class MockMessage:
            def __init__(self, entities):
                self.entities = entities

        # 1. Message with emoji url
        ent1 = MockEntityTextUrl("tg://emoji?id=777888")
        ent2 = MockEntityTextUrl("https://example.com")
        msg = MockMessage([ent1, ent2])

        module._patch_message_entities(msg)
        self.assertTrue(getattr(msg, "_sp_p", False))
        self.assertEqual(len(msg.entities), 2)
        self.assertEqual(msg.entities[0].document_id, 777888)
        self.assertEqual(msg.entities[1].url, "https://example.com")

        # 2. Second patch call should immediately skip due to _sp_p
        orig_ents = msg.entities
        module._patch_message_entities(msg)
        self.assertIs(msg.entities, orig_ents)

    def test_exteragram_sync_in_progress_guard(self):
        module = load_plugin_module("sync_exteragram.plugin")
        plugin = module.Plugin()
        self.assertFalse(plugin._sync_in_progress)

        plugin._sync_in_progress = True
        # Calling _sync_database while in progress should exit immediately
        plugin._sync_database(show_bulletin=False)
        self.assertTrue(plugin._sync_in_progress)
        plugin._sync_in_progress = False

    def test_profile_activity_cell_injection(self):
        for mod_file in ("sync_ayugram.plugin", "sync_exteragram.plugin"):
            module = load_plugin_module(mod_file)
            plugin = module.Plugin()

            plugin._profiles_snapshot = {
                1001: {"name_color": 1, "profile_color": 2, "emoji_status_id": 0}
            }

            class MockViewClass:
                def __init__(self, simple_name):
                    self._simple_name = simple_name
                def getSimpleName(self):
                    return self._simple_name

            class MockTextDetailCell:
                def __init__(self, ctx=None):
                    self.text = ""
                    self.subtext = ""
                    self.need_divider = False
                    self.tag = None
                    self.click_listener = None
                def getClass(self):
                    return MockViewClass("TextDetailCell")
                def setTextAndValue(self, text, subtext, need_divider=False):
                    self.text = text
                    self.subtext = subtext
                    self.need_divider = need_divider
                def setTag(self, tag):
                    self.tag = tag
                def setOnClickListener(self, listener):
                    self.click_listener = listener

            class MockLinearLayout:
                def __init__(self):
                    self.children = []
                def getClass(self):
                    return MockViewClass("LinearLayout")
                def getChildCount(self):
                    return len(self.children)
                def getChildAt(self, i):
                    return self.children[i]
                def addView(self, view):
                    self.children.append(view)
                def findViewWithTag(self, tag):
                    for c in self.children:
                        if getattr(c, "tag", None) == tag:
                            return c
                    return None

            class MockFragment:
                def __init__(self, uid, ll):
                    self.user_id = uid
                    self.linearLayout = ll
                def getFragmentView(self):
                    return self.linearLayout
                def getParentActivity(self):
                    return "MockActivityContext"

            orig_find_class = module.find_class
            try:
                module.find_class = lambda name: MockTextDetailCell if name == "org.telegram.ui.Cells.TextDetailCell" else None

                ll = MockLinearLayout()
                # Simulate existing child (birthday cell)
                existing_child = MockTextDetailCell()
                existing_child.needDivider = False
                ll.addView(existing_child)

                frag = MockFragment(1001, ll)
                plugin._inject_profile_activity_cell(frag)

                # Verify cell was injected
                self.assertEqual(len(ll.children), 2)
                injected = ll.children[1]
                self.assertEqual(injected.text, "Этот пользователь использует SyncProfile")
                self.assertEqual(injected.subtext, "SyncProfile")
                self.assertEqual(injected.tag, "syncprofile_detail_cell")
                self.assertTrue(existing_child.needDivider)

                # Duplicate call should not add duplicate cell
                plugin._inject_profile_activity_cell(frag)
                self.assertEqual(len(ll.children), 2)

                # Non-sync user should not inject
                ll2 = MockLinearLayout()
                frag2 = MockFragment(9999, ll2)
                plugin._inject_profile_activity_cell(frag2)
                self.assertEqual(len(ll2.children), 0)

                # Own user ID should also inject
                plugin._get_my_active_uids = lambda: [5555]
                ll3 = MockLinearLayout()
                frag3 = MockFragment(5555, ll3)
                plugin._inject_profile_activity_cell(frag3)
                self.assertEqual(len(ll3.children), 1)
                self.assertEqual(ll3.children[0].text, "Этот пользователь использует SyncProfile")
            finally:
                module.find_class = orig_find_class

    def test_user_full_and_chat_full_permanent_signature(self):
        for mod_file in ("sync_ayugram.plugin", "sync_exteragram.plugin"):
            module = load_plugin_module(mod_file)
            plugin = module.Plugin()

            plugin._profiles_snapshot = {
                1001: {"name_color": 1, "profile_color": 2, "emoji_status_id": 0}
            }
            plugin._chats_snapshot = {
                2002: {"name_color": 3, "profile_color": 4, "emoji_status_id": 0}
            }

            class MockUserFull:
                def __init__(self, uid, about=""):
                    self.id = uid
                    self.about = about
                    self.flags = 0
                    self.color = None
                    self.profile_color = None
                    self.custom_status = None
                    self.emoji_status = None
                    self.user = None

            class MockChatFull:
                def __init__(self, cid, about=""):
                    self.id = cid
                    self.about = about
                    self.flags = 0
                    self.color = None
                    self.profile_color = None
                    self.custom_status = None
                    self.emoji_status = None
                    self.chat = None
                    self.boosts_applied = 0

            # 1. Peer in sync db with existing bio
            fu1 = MockUserFull(1001, "Hello world")
            plugin._patch_full_user_tl_object(fu1, 1001)
            self.assertIn("Hello world", fu1.about)
            self.assertIn("⚡ Этот пользователь использует SyncProfile", fu1.about)
            self.assertTrue(bool(fu1.flags & 2))

            # 2. Own account should also receive the signature
            plugin._get_my_active_uids = lambda: [5555]
            plugin._get_active_accounts_data = lambda: [{"acc_idx": 0, "user_id": 5555}]
            fu_own = MockUserFull(5555, "My own bio")
            plugin._patch_full_user_tl_object(fu_own, 5555)
            self.assertIn("My own bio", fu_own.about)
            self.assertIn("⚡ Этот пользователь использует SyncProfile", fu_own.about)
            self.assertTrue(bool(fu_own.flags & 2))

            # 3. ChatFull
            fc1 = MockChatFull(2002, "Channel bio")
            plugin._patch_full_chat_tl_object(fc1, 2002)
            self.assertIn("Channel bio", fc1.about)
            self.assertIn("⚡ Этот чат/канал использует SyncProfile", fc1.about)
            self.assertTrue(bool(fc1.flags & 2))

    def test_custom_emoji_pre_post_request_hooks_both_clients(self):
        for mod_file in ("sync_ayugram.plugin", "sync_exteragram.plugin"):
            module = load_plugin_module(mod_file)
            plugin = module.Plugin()

            class MockTLRPC:
                class TL_messageEntityCustomEmoji:
                    def __init__(self, offset=0, length=2, document_id=123456789):
                        self.offset = offset
                        self.length = length
                        self.document_id = document_id
                class TL_messageEntityTextUrl:
                    def __init__(self, offset=0, length=2, url=""):
                        self.offset = offset
                        self.length = length
                        self.url = url

            module.TLRPC = MockTLRPC

            # 1. Test pre_request_hook converts TL_messageEntityCustomEmoji -> TL_messageEntityTextUrl
            class MockSendMessageRequest:
                def __init__(self):
                    self.entities = [MockTLRPC.TL_messageEntityCustomEmoji(0, 2, 9988776655)]
                    self.multi_media = None

            req = MockSendMessageRequest()
            res = plugin.pre_request_hook("messages.sendMessage", 0, req)
            self.assertEqual(res.strategy, module.HookStrategy.MODIFY)
            self.assertEqual(len(req.entities), 1)
            self.assertIsInstance(req.entities[0], MockTLRPC.TL_messageEntityTextUrl)
            self.assertEqual(req.entities[0].url, "tg://emoji?id=9988776655")

            # 2. Test post_request_hook / on_update_hook converts tg://emoji?id=... back to TL_messageEntityCustomEmoji
            class MockMessage:
                def __init__(self):
                    self.entities = [MockTLRPC.TL_messageEntityTextUrl(0, 2, "tg://emoji?id=9988776655")]

            class MockUpdate:
                def __init__(self):
                    self.message = MockMessage()

            upd = MockUpdate()
            plugin.on_update_hook("updateNewMessage", 0, upd)
            self.assertEqual(len(upd.message.entities), 1)
            self.assertIsInstance(upd.message.entities[0], MockTLRPC.TL_messageEntityCustomEmoji)
            self.assertEqual(upd.message.entities[0].document_id, 9988776655)

if __name__ == "__main__":
    unittest.main()


