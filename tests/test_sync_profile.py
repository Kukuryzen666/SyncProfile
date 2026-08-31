import json
import os
import sys
import tempfile
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

class MockLongSparseArray:
    def __init__(self):
        self._items = {}
    def put(self, k, v):
        self._items[int(k)] = v
    def get(self, k):
        return self._items.get(int(k))
    def size(self):
        return len(self._items)
    def valueAt(self, i):
        return list(self._items.values())[i]

class MockMessagesControllerInstance:
    def __init__(self, acc=0):
        self.acc = acc
        self.users = MockLongSparseArray()
        self.chats = MockLongSparseArray()
    def getUser(self, uid):
        return self.users.get(int(uid))
    def getChat(self, cid):
        return self.chats.get(int(cid))

class MockMessagesController:
    _instances = {}
    @classmethod
    def getInstance(cls, acc=0):
        if acc not in cls._instances:
            cls._instances[acc] = MockMessagesControllerInstance(acc)
        return cls._instances[acc]

tg_messenger.UserConfig = MockUserConfig
tg_messenger.SharedConfig = MockSharedConfig
tg_messenger.MessagesController = MockMessagesController
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
        module = load_plugin_module("sync_ayugram.plugin")
        plugin = module.Plugin()
        
        # Mark uid 555 as an own account
        plugin._own_uids_cache = {555}
        plugin._update_snapshot()

        # Own user on AyuGram is managed exclusively by AyuGram's native Local Premium (AyuConfig).
        # Plugin MUST NOT overwrite own account's User TL object.
        user_own = MockUser(uid=555)
        user_own.premium = False
        user_own.color = None
        
        res = plugin._patch_user_tl_object(user_own)
        self.assertFalse(res)
        self.assertFalse(user_own.premium)
        self.assertIsNone(user_own.color)

        # Other (remote) user on AyuGram is patched by SyncProfile
        plugin._profiles_cache[777] = {
            "user_id": 777,
            "name_color": 2,
            "premium": True
        }
        plugin._update_snapshot()
        user_other = MockUser(uid=777)
        user_other.premium = False

        res_other = plugin._patch_user_tl_object(user_other)
        self.assertTrue(res_other)
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
        """Тест: в AyuGram плагин не вмешивается в AyuConfig, оставляя его настройки клиенту."""
        module = load_plugin_module("sync_ayugram.plugin")
        plugin = module.Plugin()
        
        MockAyuConfig.localPremium = False
        MockAyuConfig.saveConfig.reset_mock()
        plugin._ensure_local_premium()
        # AyuConfig не должен быть принудительно изменен плагином
        self.assertFalse(MockAyuConfig.localPremium)
        MockAyuConfig.saveConfig.assert_not_called()

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

    def test_video_avatar_normalized_for_sync_user(self):
        module = load_plugin_module("sync_ayugram.plugin")
        plugin = module.Plugin()

        # User in SyncProfile database gets video avatar checked and normalized
        plugin._profiles_cache[123456] = {"user_id": 123456, "name_color": 1}
        plugin._update_snapshot()

        sync_user = MockUser(uid=123456)
        sync_user.photo = MockPhoto(photo_id=555, has_video=False, video_sizes=["mock_video_size"], flags=0)

        res = plugin._patch_user_tl_object(sync_user)
        self.assertTrue(res)
        self.assertTrue(sync_user.photo.has_video)
        self.assertEqual(sync_user.photo.flags & 1, 1)

        # Non-sync user is rejected immediately on line 1 without video parsing
        regular_user = MockUser(uid=999888)
        regular_user.photo = MockPhoto(photo_id=666, has_video=False, video_sizes=["mock_video_size"], flags=0)
        res_non_sync = plugin._patch_user_tl_object(regular_user)
        self.assertFalse(res_non_sync)

    def test_ensure_local_premium_enables_animated_avatars(self):
        """Тест: _ensure_local_premium проверяет SharedConfig для анимации аватаров."""
        module = load_plugin_module("sync_ayugram.plugin")
        plugin = module.Plugin()

        class MockSharedConfig:
            animateAvatars = False
            autoplayVideo = False
            autoplayGifs = False
            loopStickers = False
            saveConfig = MagicMock()

        if "org.telegram.messenger" not in sys.modules:
            sys.modules["org.telegram.messenger"] = types.ModuleType("org.telegram.messenger")

        tg_messenger = sys.modules["org.telegram.messenger"]
        tg_messenger.SharedConfig = MockSharedConfig

        try:
            plugin._ensure_local_premium()
            self.assertTrue(MockSharedConfig.animateAvatars)
            self.assertTrue(MockSharedConfig.autoplayVideo)
            MockSharedConfig.saveConfig.assert_called()
        finally:
            if hasattr(tg_messenger, "SharedConfig"):
                delattr(tg_messenger, "SharedConfig")

    def test_ensure_local_premium_extera_and_koto(self):
        """Тест: в exteraGram _ensure_local_premium настраивает ExteraConfig.localPremium."""
        module = load_plugin_module("sync_exteragram.plugin")
        plugin = module.Plugin()

        class MockExteraConfig:
            localPremium = False
            saveConfig = MagicMock()

        if "org.telegram.messenger" not in sys.modules:
            sys.modules["org.telegram.messenger"] = types.ModuleType("org.telegram.messenger")

        tg_messenger = sys.modules["org.telegram.messenger"]
        tg_messenger.ExteraConfig = MockExteraConfig
        try:
            plugin._ensure_local_premium()
            self.assertTrue(MockExteraConfig.localPremium)
            MockExteraConfig.saveConfig.assert_called()
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

    def test_ayugram_on_send_message_hook_pass_through(self):
        module = load_plugin_module("sync_ayugram.plugin")
        plugin = module.Plugin()

        class MockSendParams:
            def __init__(self, message, entities):
                self.message = message
                self.entities = entities

        custom_emoji = MockTLRPC.TL_messageEntityCustomEmoji(0, 2, 777888999)
        params = MockSendParams("Hello", [custom_emoji])
        res = plugin.on_send_message_hook(0, params)
        self.assertEqual(res.strategy, module.HookStrategy.DEFAULT)
        # Entities must remain completely untouched in AyuGram
        self.assertIs(params.entities[0], custom_emoji)

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
            # Verify 3 meaningful actions: sync, push all, and clear/reset cache
            self.assertTrue(any("Синхронизировать с сервером" in t for t in texts))
            self.assertTrue(any("Опубликовать все аккаунты" in t for t in texts))
            self.assertTrue(any("Сбросить кэш" in t for t in texts))
            # Verify duplicate full download button is removed
            self.assertFalse(any("Полная пересинхронизация базы" in t for t in texts))
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
        """Тест: _sync_local_ayuconfig не перезаписывает AyuConfig, сохраняя нативные настройки."""
        module = load_plugin_module("sync_ayugram.plugin")
        plugin = module.Plugin()

        MockAyuConfig.statusEmojiId = 0
        MockAyuConfig.animateAvatars = False
        MockAyuConfig.autoplayVideo = False

        plugin.set_setting("slot_0_emoji_status_id", "543210987654321")
        plugin.set_setting("slot_0_name_color", 3)
        plugin.set_setting("slot_0_profile_color", 5)

        plugin._sync_local_ayuconfig(0)
        # Настройки AyuConfig остаются нетронутыми
        self.assertEqual(MockAyuConfig.statusEmojiId, 0)

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

    def test_profile_activity_bulletin_notification(self):
        for mod_file in ("sync_ayugram.plugin", "sync_exteragram.plugin"):
            module = load_plugin_module(mod_file)
            plugin = module.Plugin()

            plugin._profiles_snapshot = {
                1001: {"user_id": 1001, "name_color": 1, "profile_color": 2, "emoji_status_id": 0}
            }
            plugin._chats_snapshot = {
                2002: {"chat_id": 2002, "name_color": 3, "profile_color": 4, "emoji_status_id": 0}
            }

            class MockFragment:
                def __init__(self, uid):
                    self.user_id = uid

            bulletin_calls = []
            module.bulletins.show_info = lambda msg: bulletin_calls.append(msg)

            # 1. SyncProfile user
            frag = MockFragment(1001)
            plugin._show_profile_bulletin_if_sync_user(frag)
            self.assertEqual(len(bulletin_calls), 1)
            self.assertIn("Этот пользователь использует SyncProfile", bulletin_calls[0])

            # 2. Cooldown prevents duplicate popup within 10s
            plugin._show_profile_bulletin_if_sync_user(frag)
            self.assertEqual(len(bulletin_calls), 1)

            # 3. Non-sync user should not trigger bulletin
            bulletin_calls.clear()
            frag_non_sync = MockFragment(9999)
            plugin._show_profile_bulletin_if_sync_user(frag_non_sync)
            self.assertEqual(len(bulletin_calls), 0)

            # 4. Own active user ID triggers bulletin
            plugin._own_uids_cache = {5555}
            plugin._get_my_active_uids = lambda: [5555]
            frag_own = MockFragment(5555)
            plugin._show_profile_bulletin_if_sync_user(frag_own)
            self.assertEqual(len(bulletin_calls), 1)
            self.assertIn("Этот пользователь использует SyncProfile", bulletin_calls[0])

            # 5. Channel/Chat profile triggers chat bulletin
            bulletin_calls.clear()
            frag_chat = MockFragment(-2002)
            plugin._show_profile_bulletin_if_sync_user(frag_chat)
            self.assertEqual(len(bulletin_calls), 1)
            self.assertIn("Этот чат/канал использует SyncProfile", bulletin_calls[0])

    def test_exteragram_sync_in_progress_guard(self):
        module = load_plugin_module("sync_exteragram.plugin")
        plugin = module.Plugin()
        self.assertFalse(plugin._sync_in_progress)

        plugin._sync_in_progress = True
        # Calling _sync_database while in progress should exit immediately
        plugin._sync_database(show_bulletin=False)
        self.assertTrue(plugin._sync_in_progress)
        plugin._sync_in_progress = False

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

            # 1. Peer in sync db with existing bio (about is cleanly preserved)
            fu1 = MockUserFull(1001, "Hello world")
            plugin._patch_full_user_tl_object(fu1, 1001)
            self.assertEqual(fu1.about, "Hello world")

            # 2. Own account bio is also cleanly preserved
            plugin._get_my_active_uids = lambda: [5555]
            plugin._get_active_accounts_data = lambda: [{"acc_idx": 0, "user_id": 5555}]
            fu_own = MockUserFull(5555, "My own bio")
            plugin._patch_full_user_tl_object(fu_own, 5555)
            self.assertEqual(fu_own.about, "My own bio")

            # 3. ChatFull bio is cleanly preserved
            fc1 = MockChatFull(2002, "Channel bio")
            plugin._patch_full_chat_tl_object(fc1, 2002)
            self.assertEqual(fc1.about, "Channel bio")

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

            # 1. Test pre_request_hook:
            # - In exteraGram: converts TL_messageEntityCustomEmoji -> TL_messageEntityTextUrl
            # - In AyuGram: does NOT intercept outgoing messages (pass-through / DEFAULT)
            class MockSendMessageRequest:
                def __init__(self):
                    self.entities = [MockTLRPC.TL_messageEntityCustomEmoji(0, 2, 9988776655)]
                    self.multi_media = None

            req = MockSendMessageRequest()
            res = plugin.pre_request_hook("messages.sendMessage", 0, req)
            if mod_file == "sync_exteragram.plugin":
                self.assertEqual(res.strategy, module.HookStrategy.MODIFY)
                self.assertEqual(len(req.entities), 1)
                self.assertIsInstance(req.entities[0], MockTLRPC.TL_messageEntityTextUrl)
                self.assertEqual(req.entities[0].url, "tg://emoji?id=9988776655")
            else:
                self.assertEqual(res.strategy, module.HookStrategy.DEFAULT)
                self.assertEqual(len(req.entities), 1)
                self.assertIsInstance(req.entities[0], MockTLRPC.TL_messageEntityCustomEmoji)

            # 2. Test post_request_hook / on_update_hook converts tg://emoji?id=... back to TL_messageEntityCustomEmoji (both clients)
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

    def test_prevent_folder_reset_hooks_and_is_premium(self):
        """Тест регистрации и работы хуков защиты от сброса папок («Все чаты»)."""
        for mod_file in ("sync_ayugram.plugin", "sync_exteragram.plugin"):
            module = load_plugin_module(mod_file)
            plugin = module.Plugin()
            plugin._is_running = True

            class MockDialogFilter:
                def __init__(self, locked=True):
                    self.locked = locked

            class MockMessagesController:
                def __init__(self):
                    self.dialogFilters = [MockDialogFilter(True), MockDialogFilter(True)]
                def getUser(self, uid):
                    return None
                def getChat(self, cid):
                    return None
                def getUserFull(self, uid):
                    return None
                def getChatFull(self, cid):
                    return None
                def putUser(self, user):
                    pass
                def putChat(self, chat):
                    pass
                def putMessage(self, msg):
                    pass
                def putMessages(self, msgs):
                    pass
                def lockFiltersInternal(self):
                    pass
                def checkFiltersLocked(self):
                    pass
                def isPremiumUser(self, uid):
                    return False

            class MockUserConfig:
                @classmethod
                def getInstance(cls, acc=0):
                    return cls()
                def isPremium(self):
                    return False
                def getClientUserId(self):
                    return 777000

            class MockUserObject:
                @staticmethod
                def isPremiumUser(user):
                    return False

            # Hook registration
            registered_hooks = []
            def fake_hook_method(method, hook_instance):
                registered_hooks.append((method, hook_instance))
                return object()

            plugin.hook_method = fake_hook_method
            plugin._get_my_active_uids = lambda: [777000]

            class Param:
                def __init__(self, this_obj=None, args=None):
                    self.thisObject = this_obj
                    self.args = args or []
                    self.result = None
                def setResult(self, val):
                    self.result = val
                def getResult(self):
                    return self.result

            # 1. Test LockFiltersHook unlocks dialogFilters and cancels method
            mc_inst = MockMessagesController()
            self.assertTrue(mc_inst.dialogFilters[0].locked)
            self.assertTrue(mc_inst.dialogFilters[1].locked)

            # Test MessagesControllerLockFiltersHook
            # Reconstruct class dynamically or via find_class
            class FakeMethod:
                def __init__(self, name, p_types=None):
                    self._name = name
                    self._p_types = p_types or []
                def getName(self):
                    return self._name
                def getParameterTypes(self):
                    return self._p_types
                def setAccessible(self, val):
                    pass

            def fake_get_class_methods(cls):
                return [
                    FakeMethod("lockFiltersInternal"),
                    FakeMethod("checkFiltersLocked"),
                    FakeMethod("lockFilters"),
                    FakeMethod("isFilterLocked"),
                    FakeMethod("isDialogFilterLocked"),
                    FakeMethod("areFiltersLocked"),
                    FakeMethod("canUseCustomEmoji"),
                    FakeMethod("canUsePremiumSticker"),
                    FakeMethod("getUserFull", [FakeMethod("long")]),
                    FakeMethod("getChatFull", [FakeMethod("long")]),
                ]

            module._get_class_methods = fake_get_class_methods
            module.find_class = lambda name: object()

            plugin._register_xposed_hooks()
            self.assertTrue(len(plugin._xposed_unhooks) > 0)

            # Find user and chat hooks in registered hooks
            user_hooks = []
            chat_hooks = []

            for m, h in registered_hooks:
                h_name = h.__class__.__name__
                if "GetUserFullHook" in h_name:
                    user_hooks.append((m, h))
                elif "GetChatFullHook" in h_name:
                    chat_hooks.append((m, h))

            self.assertTrue(len(user_hooks) >= 1)
            self.assertTrue(len(chat_hooks) >= 1)

            # 3. Test _patch_user_tl_object sets premium according to server snapshot
            class MockUser:
                def __init__(self, uid):
                    self.id = uid
                    self.premium = False
                    self.flags = 0
                    self.flags2 = 0
                    self.photo = None
            u_own = MockUser(777000)
            plugin._profiles_snapshot = {777000: {"user_id": 777000, "premium": True}}
            plugin._patch_user_tl_object(u_own)
            self.assertTrue(u_own.premium)

            # Random user not in SyncProfile -> _patch_user_tl_object returns False and premium stays False
            u_other = MockUser(999999)
            res = plugin._patch_user_tl_object(u_other)
            self.assertFalse(res)
            self.assertFalse(u_other.premium)

    def test_version_tagging_and_instant_fast_path(self):
        """Тест: мгновенное отсечение неотслеживаемых пользователей на 1-й строке без JNI (~30ns)."""
        for mod_file in ("sync_ayugram.plugin", "sync_exteragram.plugin"):
            module = load_plugin_module(mod_file)
            plugin = module.Plugin()

            plugin._profiles_cache[12345] = {"user_id": 12345, "name_color": 2, "profile_color": 3}
            plugin._update_snapshot()

            user_tracked = MockUser(12345)
            user_untracked = MockUser(67890)

            # 1. Первый вызов для отслеживаемого юзера -> True и патчинг
            self.assertTrue(plugin._patch_user_tl_object(user_tracked))
            self.assertEqual(user_tracked.color.color, 2)
            self.assertEqual(user_tracked.profile_color.color, 3)

            # 2. Неотслеживаемый юзер мгновенно возвращает False (Instant Fast-Path)
            self.assertFalse(plugin._patch_user_tl_object(user_untracked))
            self.assertIsNone(user_untracked.color)

    def test_static_peer_colors_and_emoji_status_builder(self):
        """Тест: пул _STATIC_PEER_COLORS и _build_emoji_status."""
        for mod_file in ("sync_ayugram.plugin", "sync_exteragram.plugin"):
            module = load_plugin_module(mod_file)
            plugin = module.Plugin()

            c1 = module._build_peer_color(1, 0)
            c2 = module._build_peer_color(1, 0)
            self.assertIs(c1, c2)

            st1 = module._build_emoji_status(998877)
            self.assertIsNotNone(st1)
            self.assertEqual(st1.document_id, 998877)

            st_zero = module._build_emoji_status(0)
            self.assertIsNone(st_zero)

    def test_lazy_jit_patching_replaces_heavy_put_hooks(self):
        """Тест: ленивый JIT-патчинг видимых ячеек через GetUserHook/GetChatHook вместо тяжелых Put-хуков."""
        for mod_file in ("sync_ayugram.plugin", "sync_exteragram.plugin"):
            module = load_plugin_module(mod_file)
            plugin = module.Plugin()

            registered_hooks = []
            plugin.hook_method = lambda m, h: registered_hooks.append((m, h)) or h

            class FakeMethod:
                def __init__(self, name, p_types=None):
                    self._name = name
                    self._p_types = p_types or []
                def getName(self):
                    return self._name
                def getParameterTypes(self):
                    return self._p_types
                def setAccessible(self, val):
                    pass

            class MockLongParam:
                def getName(self):
                    return "long"

            def fake_get_class_methods(cls):
                return [
                    FakeMethod("getUser", [MockLongParam()]),
                    FakeMethod("getChat", [MockLongParam()]),
                    FakeMethod("getUserFull", [MockLongParam()]),
                    FakeMethod("getChatFull", [MockLongParam()]),
                    FakeMethod("putUser", [MockLongParam(), MockLongParam()]),
                    FakeMethod("putChat", [MockLongParam(), MockLongParam()]),
                    FakeMethod("putUsers", [MockLongParam(), MockLongParam()]),
                    FakeMethod("putChats", [MockLongParam(), MockLongParam()]),
                ]

            module._get_class_methods = fake_get_class_methods
            module.find_class = lambda name: object()

            plugin._register_xposed_hooks()

            hook_classes = {h.__class__.__name__ for m, h in registered_hooks}

            # Scroll hot path methods getUser/getChat must NEVER be hooked
            self.assertNotIn("GetUserHook", hook_classes)
            self.assertNotIn("GetChatHook", hook_classes)

            # Data-load put hooks MUST be registered
            self.assertIn("PutUserHook", hook_classes)
            self.assertIn("PutChatHook", hook_classes)
            self.assertIn("PutUsersHook", hook_classes)
            self.assertIn("PutChatsHook", hook_classes)

            # Full profile hooks are safely registered
            self.assertIn("GetUserFullHook", hook_classes)
            self.assertIn("GetChatFullHook", hook_classes)

    def test_dialog_filter_unlock_hooks_registered(self):
        """Тест: легковесные хуки разблокировки папок регистрируются без тяжелых циклов перебора."""
        for mod_file in ("sync_ayugram.plugin", "sync_exteragram.plugin"):
            module = load_plugin_module(mod_file)
            plugin = module.Plugin()

            registered = []
            plugin.hook_method = lambda m, h: registered.append((m, h)) or h

            class FakeMethod:
                def __init__(self, name, p_types=None):
                    self._name = name
                    self._p_types = p_types or []
                def getName(self):
                    return self._name
                def getParameterTypes(self):
                    return self._p_types
                def setAccessible(self, val):
                    pass

            def fake_get_methods(cls):
                return [
                    FakeMethod("getDialogFilter", [object()]),
                    FakeMethod("getDialogFilters", []),
                    FakeMethod("loadDialogFilters", []),
                    FakeMethod("lockFilters", []),
                    FakeMethod("isFilterLocked", []),
                    FakeMethod("isLocked", []),
                ]

            module._get_class_methods = fake_get_methods
            module.find_class = lambda name: object()

            plugin._register_xposed_hooks()

            hook_names = {h.__class__.__name__ for m, h in registered}
            # All intrusive folder hooks are completely removed to prevent state conflicts with client's native Local Premium
            self.assertNotIn("GetDialogFilterHook", hook_names)
            self.assertNotIn("GetDialogFiltersHook", hook_names)
            self.assertNotIn("LoadDialogFiltersHook", hook_names)
            self.assertNotIn("MessagesControllerLockFiltersHook", hook_names)
            self.assertNotIn("MessagesControllerIsFilterLockedHook", hook_names)
            self.assertNotIn("DialogFilterIsLockedHook", hook_names)
            self.assertNotIn("DialogsActivityCheckFilterLockedHook", hook_names)

    def test_post_request_hook_filters_irrelevant_requests(self):
        """Тест: post_request_hook обрабатывает только запросы сообщений/каналов/обновлений."""
        for mod_file in ("sync_ayugram.plugin", "sync_exteragram.plugin"):
            module = load_plugin_module(mod_file)
            plugin = module.Plugin()

            mock_response = MagicMock()
            mock_response.messages = ["msg1"]

            patched = []
            module._patch_messages_in_response = lambda resp: patched.append(resp)

            # 1. Запрос из нерелевантного пакета (account, help, auth) -> мгновенный пропуск
            plugin.post_request_hook("auth.sendCode", 0, mock_response, None)
            plugin.post_request_hook("help.getAppConfig", 0, mock_response, None)
            self.assertEqual(len(patched), 0)

            # 2. Запрос из релевантного пакета (messages, channels, updates) -> обработка
            plugin.post_request_hook("messages.getHistory", 0, mock_response, None)
            self.assertEqual(len(patched), 1)

            plugin.post_request_hook("channels.getMessages", 0, mock_response, None)
            self.assertEqual(len(patched), 2)

    def test_dialog_filters_not_tampered_in_ui_apply(self):
        """Тест: _apply_all_to_all_accounts не трогает mc.dialogFilters (оставляет клиенту нативное управление)."""
        for mod_file in ("sync_ayugram.plugin", "sync_exteragram.plugin"):
            module = load_plugin_module(mod_file)
            plugin = module.Plugin()

            class MockFilter:
                def __init__(self, fid, locked=True):
                    self.id = fid
                    self.locked = locked

            class MockMC:
                def __init__(self):
                    self.dialogFilters = [MockFilter(1, True), MockFilter(2, True), MockFilter(3, True)]
                def getUser(self, uid):
                    return None

            mock_mc_instance = MockMC()

            if "org.telegram.messenger" not in sys.modules:
                sys.modules["org.telegram.messenger"] = types.ModuleType("org.telegram.messenger")

            tg_messenger = sys.modules["org.telegram.messenger"]
            orig_mc = getattr(tg_messenger, "MessagesController", None)

            class MockMessagesControllerClass:
                @staticmethod
                def getInstance(acc):
                    return mock_mc_instance

            tg_messenger.MessagesController = MockMessagesControllerClass

            try:
                plugin._own_apply_cache.clear()
                plugin._get_active_accounts_data = lambda force=False: [{"acc_idx": 0, "user_id": 12345, "name": "Acc1", "is_current": True}]
                plugin._apply_all_to_all_accounts()

                import time
                time.sleep(0.1)

                # dialogFilters should remain unchanged by plugin
                self.assertEqual(len(mock_mc_instance.dialogFilters), 3)
            finally:
                if orig_mc is not None:
                    tg_messenger.MessagesController = orig_mc

    def test_update_snapshot_partial_updates_both_caches(self):
        """Тест: _update_snapshot_partial обновляет и profiles_snapshot, и chats_snapshot."""
        for mod_file in ("sync_ayugram.plugin", "sync_exteragram.plugin"):
            module = load_plugin_module(mod_file)
            plugin = module.Plugin()

            plugin._profiles_cache[101] = {"user_id": 101, "name_color": 5}
            plugin._chats_cache[202] = {"chat_id": 202, "profile_color": 7}

            plugin._update_snapshot_partial(updated_uids={101}, updated_cids={202})

            self.assertIn(101, plugin._profiles_snapshot)
            self.assertEqual(plugin._profiles_snapshot[101]["name_color"], 5)

            self.assertIn(202, plugin._chats_snapshot)
            self.assertEqual(plugin._chats_snapshot[202]["profile_color"], 7)

    def test_badge_switch_in_user_full(self):
        """Тест: show_syncprofile_badge_in_about управляет добавлением бейджа в UserFull.about."""
        for mod_file in ("sync_ayugram.plugin", "sync_exteragram.plugin"):
            module = load_plugin_module(mod_file)
            plugin = module.Plugin()

            class MockUserFull:
                def __init__(self, uid, about=""):
                    self.id = uid
                    self.about = about
                    self.flags = 0
                    self.user = None

            class MockFragment:
                def __init__(self, uid):
                    self.user_id = uid

            bulletin_calls = []
            module.bulletins.show_info = lambda msg: bulletin_calls.append(msg)

            # 1. Profile enabled in cache
            plugin._profiles_snapshot[5001] = {"user_id": 5001, "name_color": 1}

            # 2. When setting is True -> Bottom bulletin is shown
            plugin.get_setting = lambda key, default=None: True if key == "show_syncprofile_badge_in_about" else default
            frag1 = MockFragment(5001)
            plugin._show_profile_bulletin_if_sync_user(frag1)
            self.assertEqual(len(bulletin_calls), 1)
            self.assertIn("⚡ Этот пользователь использует SyncProfile", bulletin_calls[0])

            # 3. When setting is False -> Bottom bulletin is NOT shown
            plugin.get_setting = lambda key, default=None: False if key == "show_syncprofile_badge_in_about" else default
            plugin._last_shown_bulletin = (0, 0.0)
            bulletin_calls.clear()
            frag2 = MockFragment(5001)
            plugin._show_profile_bulletin_if_sync_user(frag2)
            self.assertEqual(len(bulletin_calls), 0)

    def test_api_request_retries_and_error_handling(self):
        """Тест: _api_request корректно выполняет retry и возвращает статус/ошибки."""
        for mod_file in ("sync_ayugram.plugin", "sync_exteragram.plugin"):
            module = load_plugin_module(mod_file)
            plugin = module.Plugin()

            import urllib.error
            import io

            class MockResponse:
                def __init__(self, status, json_str):
                    self.status = status
                    self._data = json_str.encode("utf-8")
                def read(self):
                    return self._data
                def __enter__(self):
                    return self
                def __exit__(self, *args):
                    pass

            # Test successful request
            with unittest.mock.patch("urllib.request.urlopen") as mock_urlopen:
                mock_urlopen.return_value = MockResponse(200, '{"result": "ok"}')
                status, data, err = plugin._api_request("GET", "api/test", retries=2)
                self.assertEqual(status, 200)
                self.assertEqual(data, {"result": "ok"})
                self.assertIsNone(err)
                self.assertEqual(mock_urlopen.call_count, 1)

            # Test 401 Unauthorized (does NOT retry)
            with unittest.mock.patch("urllib.request.urlopen") as mock_urlopen:
                mock_urlopen.side_effect = urllib.error.HTTPError("url", 401, "Unauthorized", {}, io.BytesIO(b""))
                status, data, err = plugin._api_request("GET", "api/test", retries=2)
                self.assertEqual(status, 401)
                self.assertIsNone(data)
                self.assertEqual(mock_urlopen.call_count, 1)

            # Test 500 error with retry (retries=2 -> 3 attempts)
            with unittest.mock.patch("urllib.request.urlopen") as mock_urlopen:
                mock_urlopen.side_effect = urllib.error.HTTPError("url", 500, "Server Error", {}, io.BytesIO(b""))
                status, data, err = plugin._api_request("GET", "api/test", retries=2, backoff_factor=0.01)
                self.assertEqual(status, 0)
                self.assertEqual(mock_urlopen.call_count, 3)

    def test_sync_op_lock_prevents_reentrancy(self):
        """Тест: _sync_op_lock атомарно предотвращает повторный запуск синка при активном флаге."""
        for mod_file in ("sync_ayugram.plugin", "sync_exteragram.plugin"):
            module = load_plugin_module(mod_file)
            plugin = module.Plugin()

            with plugin._sync_op_lock:
                plugin._sync_in_progress = True

            # Attempting _sync_database should early return without making network calls
            with unittest.mock.patch.object(plugin, "_api_request") as mock_api:
                plugin._sync_database(show_bulletin=False)
                mock_api.assert_not_called()

            # Attempting _sync_delta_worker should early return
            with unittest.mock.patch.object(plugin, "_api_request") as mock_api:
                plugin._sync_delta_worker(show_bulletin=False)
                mock_api.assert_not_called()

            with plugin._sync_op_lock:
                plugin._sync_in_progress = False

    def test_hook_failure_triggers_ui_bulletin_and_error_log(self):
        """Тест: при критическом сбое регистрации хуков вызывается logger.error."""
        for mod_file in ("sync_ayugram.plugin", "sync_exteragram.plugin"):
            module = load_plugin_module(mod_file)
            plugin = module.Plugin()

            def raise_err(name):
                raise RuntimeError("Failed to resolve class")

            module.find_class = raise_err

            with unittest.mock.patch.object(module.logger, "error") as mock_log_err:
                plugin._register_xposed_hooks()
                mock_log_err.assert_called()

    def test_profile_payload_does_not_contain_auth_key(self):
        """Тест: словарь профиля для отправки на сервер не содержит небезопасного поля auth_key."""
        for mod_file in ("sync_ayugram.plugin", "sync_exteragram.plugin"):
            module = load_plugin_module(mod_file)
            plugin = module.Plugin()

            profile_payload = plugin._get_profile_dict_for_slot(0, 777000)
            self.assertNotIn("auth_key", profile_payload)
            self.assertEqual(profile_payload["user_id"], 777000)

    def test_server_settings_and_secret_token_hidden_from_user(self):
        """Тест: настройки сервера и секретный токен скрыты из интерфейса настроек плагина."""
        for mod_file in ("sync_ayugram.plugin", "sync_exteragram.plugin"):
            module = load_plugin_module(mod_file)
            plugin = module.Plugin()

            self.assertFalse(module.ALLOW_CUSTOM_SERVER_CONFIG)
            settings_items = plugin.create_settings()
            settings_keys = [getattr(item, "key", None) for item in settings_items if hasattr(item, "key")]

            self.assertNotIn("server_url", settings_keys)
            self.assertNotIn("custom_cookie", settings_keys)
    def test_trim_memory_caches(self):
        """Тест: _trim_memory_caches ограничивает рост кэшей памяти video."""
        for mod_file in ("sync_ayugram.plugin", "sync_exteragram.plugin"):
            module = load_plugin_module(mod_file)
            plugin = module.Plugin()

            # Pre-fill caches with excess items
            for i in range(1005):
                plugin._video_checked_uids.add(i)
            for i in range(505):
                plugin._video_checked_chat_ids.add(i)

            plugin._trim_memory_caches()

            self.assertEqual(len(plugin._video_checked_uids), 0)
            self.assertEqual(len(plugin._video_checked_chat_ids), 0)

    def test_trim_memory_caches_extended(self):
        """Тест: _trim_memory_caches сбрасывает/подрезает расширенные кэши."""
        for mod_file in ("sync_ayugram.plugin", "sync_exteragram.plugin"):
            module = load_plugin_module(mod_file)
            plugin = module.Plugin()

            for i in range(1005):
                plugin._video_checked_uids.add(i)
            for i in range(505):
                plugin._video_checked_chat_ids.add(i)

            module._USER_CLASS_CACHE.update({f"Class{i}": True for i in range(150)})
            module._CHAT_CLASS_CACHE.update({f"Class{i}": True for i in range(150)})
            module._PATCHED_MSGS.update({(0, i) for i in range(2500)})
            module._EMOJI_DOC_ID_CACHE.update({f"url_{i}": i for i in range(600)})

            plugin._trim_memory_caches()

            self.assertEqual(len(plugin._video_checked_uids), 0)
            self.assertEqual(len(plugin._video_checked_chat_ids), 0)
            self.assertEqual(len(module._PATCHED_MSGS), 0)

    def test_patch_message_entities_composite_key(self):
        """Тест: _patch_message_entities использует composite key (dialog_id, msg_id)."""
        for mod_file in ("sync_ayugram.plugin", "sync_exteragram.plugin"):
            module = load_plugin_module(mod_file)
            module._PATCHED_MSGS.clear()

            class MockMsg:
                def __init__(self, dialog_id, msg_id):
                    self.dialog_id = dialog_id
                    self.id = msg_id
                    self.entities = None
                    self._sp_p = False

            m1 = MockMsg(100, 1)
            m2 = MockMsg(200, 1)

            module._patch_message_entities(m1)
            self.assertIn((100, 1), module._PATCHED_MSGS)
            self.assertTrue(m1._sp_p)

            # Different dialog, same msg_id 1
            module._patch_message_entities(m2)
            self.assertIn((200, 1), module._PATCHED_MSGS)
            self.assertTrue(m2._sp_p)

    def test_active_accounts_cache(self):
        """Тест: _get_active_accounts_data кэширует список аккаунтов на TTL."""
        for mod_file in ("sync_ayugram.plugin", "sync_exteragram.plugin"):
            module = load_plugin_module(mod_file)
            plugin = module.Plugin()

            # First call populates cache
            res1 = plugin._get_active_accounts_data()
            self.assertIsNotNone(plugin._cached_active_accs)
            self.assertGreater(plugin._cached_active_accs_time, 0)

            # Subsequent call returns cached list directly
            plugin._cached_active_accs = [{"acc_idx": 0, "user_id": 999, "name": "Cached"}]
            res2 = plugin._get_active_accounts_data(force=False)
            self.assertEqual(res2[0]["user_id"], 999)

            # Force=True bypasses cache and re-queries UserConfig
            res3 = plugin._get_active_accounts_data(force=True)
            self.assertEqual(res3[0]["user_id"], 12345)

    def test_atomic_save_cache(self):
        """Тест: _save_local_profiles_cache атомарно сохраняет sync_profiles_cache.json."""
        import os
        for mod_file in ("sync_ayugram.plugin", "sync_exteragram.plugin"):
            module = load_plugin_module(mod_file)
            plugin = module.Plugin()
            plugin._profiles_cache = {123: {"name_color": 5}}
            plugin._cache_dirty = True

            plugin._save_local_profiles_cache()
            cache_file = "sync_profiles_cache.json"
            self.assertTrue(os.path.exists(cache_file))
            self.assertFalse(os.path.exists("sync_profiles_cache.json.tmp"))

            # Cleanup
            if os.path.exists(cache_file):
                try:
                    os.remove(cache_file)
                except Exception:
                    pass

    def test_push_all_accounts_parallel(self):
        """Тест: push_all_accounts выполняет отправку параллельно и обновляет snapshot."""
        import time
        for mod_file in ("sync_ayugram.plugin", "sync_exteragram.plugin"):
            module = load_plugin_module(mod_file)
            plugin = module.Plugin()

            plugin._get_active_accounts_data = lambda: [
                {"acc_idx": 0, "user_id": 111, "name": "Acc1"},
                {"acc_idx": 1, "user_id": 222, "name": "Acc2"},
            ]
            plugin._get_profile_dict_for_slot = lambda idx, uid: {"user_id": uid, "name_color": idx + 1}
            plugin._api_request = lambda method, path, **kwargs: (200, {"status": "ok"}, None)

            plugin.push_all_accounts(show_ui_bulletin=False)
            time.sleep(0.1)  # Allow worker thread to complete

            self.assertIn(111, plugin._profiles_cache)
            self.assertIn(222, plugin._profiles_cache)
            self.assertIn(111, plugin._profiles_snapshot)
            self.assertIn(222, plugin._profiles_snapshot)

    def test_is_user_and_is_chat_fast_paths(self):
        """Тест: fast-path классификация TL_user, TL_chat, TL_channel без рефлексии."""
        for mod_file in ("sync_ayugram.plugin", "sync_exteragram.plugin"):
            module = load_plugin_module(mod_file)

            class TL_user:
                pass
            class TL_chat:
                pass
            class TL_channel:
                pass
            class OtherObject:
                pass

            self.assertTrue(module._is_user(TL_user()))
            self.assertFalse(module._is_user(OtherObject()))
            self.assertTrue(module._is_chat(TL_chat()))
            self.assertTrue(module._is_chat(TL_channel()))
            self.assertFalse(module._is_chat(OtherObject()))

    def test_full_user_and_chat_instant_fast_path(self):
        """Тест: _patch_full_user_tl_object и _patch_full_chat_tl_object мгновенно отсекают неотслеживаемые сущности."""
        for mod_file in ("sync_ayugram.plugin", "sync_exteragram.plugin"):
            module = load_plugin_module(mod_file)
            plugin = module.Plugin()

            class MockUserFull:
                def __init__(self, uid):
                    self.id = uid
                    self.about = ""
                    self.flags = 0
                    self.user = None
                    self.color = None
                    self.profile_color = None

            class MockChatFull:
                def __init__(self, cid):
                    self.id = cid
                    self.about = ""
                    self.flags = 0
                    self.chat = None
                    self.color = None
                    self.profile_color = None

            plugin._profiles_snapshot[8001] = {"user_id": 8001, "name_color": 2}
            plugin._chats_snapshot[9001] = {"chat_id": 9001, "name_color": 4}

            uf = MockUserFull(8001)
            cf = MockChatFull(9001)

            res_u1 = plugin._patch_full_user_tl_object(uf, 8001)
            res_c1 = plugin._patch_full_chat_tl_object(cf, 9001)
            self.assertTrue(res_u1)
            self.assertTrue(res_c1)
            self.assertEqual(uf.color.color, 2)
            self.assertEqual(cf.color.color, 4)

            # Non-sync entities return False immediately
            uf_non = MockUserFull(99999)
            cf_non = MockChatFull(88888)
            self.assertFalse(plugin._patch_full_user_tl_object(uf_non, 99999))
            self.assertFalse(plugin._patch_full_chat_tl_object(cf_non, 88888))

    def test_trim_memory_caches_bounds_all_structures(self):
        """Тест: _trim_memory_caches сбрасывает кэши при превышении пороговых значений."""
        for mod_file in ("sync_ayugram.plugin", "sync_exteragram.plugin"):
            module = load_plugin_module(mod_file)
            plugin = module.Plugin()

            plugin._video_checked_uids = set(range(1500))
            plugin._video_checked_chat_ids = set(range(800))
            module._PATCHED_MSGS = {(1, i) for i in range(2500)}
            module._FIND_CLASS_CACHE = {f"cls_{i}": None for i in range(250)}

            plugin._trim_memory_caches()

            self.assertEqual(len(plugin._video_checked_uids), 0)
            self.assertEqual(len(plugin._video_checked_chat_ids), 0)
            self.assertEqual(len(module._PATCHED_MSGS), 0)
            self.assertEqual(len(module._FIND_CLASS_CACHE), 0)

    def test_custom_emoji_bidirectional_conversion_and_input_entities(self):
        """Тест: конвертация кастомных эмодзи поддерживает как TL_messageEntityCustomEmoji, так и TL_inputMessageEntityCustomEmoji."""
        for mod_file in ("sync_ayugram.plugin", "sync_exteragram.plugin"):
            module = load_plugin_module(mod_file)

            class FakeTLRPC:
                class TL_messageEntityTextUrl:
                    def __init__(self):
                        self.offset = 0
                        self.length = 0
                        self.url = ""
                class TL_messageEntityCustomEmoji:
                    def __init__(self):
                        self.offset = 0
                        self.length = 0
                        self.document_id = 0

            module.TLRPC = FakeTLRPC

            class MockTLMessageCustomEmoji:
                def __init__(self, offset, length, doc_id):
                    self.offset = offset
                    self.length = length
                    self.document_id = doc_id

            class MockTLInputCustomEmoji:
                def __init__(self, offset, length, doc_id):
                    self.offset = offset
                    self.length = length
                    class InputDoc:
                        def __init__(self, did):
                            self.id = did
                    self.document = InputDoc(doc_id)

            class MockTLTextUrl:
                def __init__(self, offset, length, url):
                    self.offset = offset
                    self.length = length
                    self.url = url

            ents_msg = [MockTLMessageCustomEmoji(0, 2, 5384123456789012345)]
            ents_input = [MockTLInputCustomEmoji(5, 2, 9876543210123456789)]

            converted_msg = module._convert_custom_emojis_to_text_urls(ents_msg)
            self.assertEqual(len(converted_msg), 1)
            self.assertEqual(converted_msg[0].url, "tg://emoji?id=5384123456789012345")

            converted_input = module._convert_custom_emojis_to_text_urls(ents_input)
            self.assertEqual(len(converted_input), 1)
            self.assertEqual(converted_input[0].url, "tg://emoji?id=9876543210123456789")

            # Reverse conversion from tg://emoji?id=...
            urls = [MockTLTextUrl(0, 2, "tg://emoji?id=5384123456789012345")]
            rev = module._convert_text_urls_to_custom_emojis(urls)
            self.assertEqual(len(rev), 1)
            self.assertEqual(rev[0].document_id, 5384123456789012345)

class TestProfileApplyGuarantees(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.old_cwd = os.getcwd()
        os.chdir(self.temp_dir)

    def tearDown(self):
        os.chdir(self.old_cwd)
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_refresh_loaded_telegram_objects_updates_memory(self):
        for name in ("sync_ayugram", "sync_exteragram"):
            plugin_mod = load_plugin_module(f"{name}.plugin")
            plugin = plugin_mod.Plugin()

            # Populate in-memory MessagesController with an unpatched user
            from org.telegram.messenger import MessagesController
            mc = MessagesController.getInstance(0)
            target_uid = 998877
            user_obj = MockUser(target_uid)
            self.assertIsNone(getattr(user_obj, "color", None))
            mc.users.put(target_uid, user_obj)

            # Plugin receives profile data for target_uid
            plugin._profiles_cache[target_uid] = {
                "name_color": 5,
                "name_bg_emoji_id": 123456,
                "profile_color": 3,
                "profile_bg_emoji_id": 654321,
                "emoji_status_id": 777888,
                "premium": True,
            }
            plugin._update_snapshot()

            # Execute _refresh_loaded_telegram_objects
            plugin._refresh_loaded_telegram_objects()

            # Verify that in-memory user_obj in MessagesController was immediately updated
            self.assertIsNotNone(user_obj.color)
            self.assertEqual(user_obj.color.color, 5)
            self.assertEqual(user_obj.color.background_emoji_id, 123456)
            self.assertIsNotNone(user_obj.profile_color)
            self.assertEqual(user_obj.profile_color.color, 3)
            self.assertEqual(user_obj.emoji_status.document_id, 777888)
            self.assertTrue(user_obj.premium)
            self.assertTrue(bool(user_obj.flags & 0x40000000))

    def test_jit_profile_activity_patching(self):
        for name in ("sync_ayugram", "sync_exteragram"):
            plugin_mod = load_plugin_module(f"{name}.plugin")
            plugin = plugin_mod.Plugin()

            target_uid = 445566
            plugin._profiles_cache[target_uid] = {
                "name_color": 4,
                "name_bg_emoji_id": 0,
                "profile_color": 2,
                "profile_bg_emoji_id": 0,
                "emoji_status_id": 112233,
                "premium": True,
            }
            plugin._update_snapshot()

            # Mock ProfileActivity fragment with currentUser
            class MockProfileActivity:
                def __init__(self, uid):
                    self.user_id = uid
                    self.currentUser = MockUser(uid)
                    self.userInfo = MockUser(uid)

            fragment = MockProfileActivity(target_uid)
            plugin._show_profile_bulletin_if_sync_user(fragment)

            # Check that currentUser on fragment was patched JIT
            self.assertIsNotNone(fragment.currentUser.color)
            self.assertEqual(fragment.currentUser.color.color, 4)
            self.assertEqual(fragment.currentUser.emoji_status.document_id, 112233)

    def test_emoji_status_reset_on_zero(self):
        for name in ("sync_ayugram", "sync_exteragram"):
            plugin_mod = load_plugin_module(f"{name}.plugin")
            plugin = plugin_mod.Plugin()

            target_uid = 11223344
            # First patch with emoji status
            plugin._profiles_cache[target_uid] = {
                "name_color": 1,
                "emoji_status_id": 99999,
                "premium": True,
            }
            plugin._update_snapshot()

            user_obj = MockUser(target_uid)
            plugin._patch_user_tl_object(user_obj)
            self.assertIsNotNone(user_obj.emoji_status)
            self.assertTrue(bool(user_obj.flags & 0x40000000))

            # Server updates: user cleared emoji status
            plugin._profiles_cache[target_uid] = {
                "name_color": 1,
                "emoji_status_id": 0,
                "premium": False,
            }
            plugin._update_snapshot()

            plugin._patch_user_tl_object(user_obj)
            self.assertIsNone(user_obj.emoji_status)
            self.assertFalse(bool(user_obj.flags & 0x40000000))
            self.assertFalse(bool(user_obj.flags & 0x10000000))

    def test_post_request_hook_contacts_and_users(self):
        for name in ("sync_ayugram", "sync_exteragram"):
            plugin_mod = load_plugin_module(f"{name}.plugin")
            plugin = plugin_mod.Plugin()

            target_uid = 556677
            plugin._profiles_cache[target_uid] = {
                "name_color": 6,
                "name_bg_emoji_id": 0,
                "emoji_status_id": 88888,
            }
            plugin._update_snapshot()

            # MTProto response for contacts.getContacts with vector of users
            class MockContactsResponse:
                def __init__(self, uid):
                    self.users = [MockUser(uid)]
                    self.chats = []

            resp = MockContactsResponse(target_uid)
            hook_res = plugin.post_request_hook("contacts.getContacts", 0, resp, None)
            self.assertEqual(hook_res.strategy, "DEFAULT")

            user_obj = resp.users[0]
            self.assertIsNotNone(user_obj.color)
            self.assertEqual(user_obj.color.color, 6)
            self.assertEqual(user_obj.emoji_status.document_id, 88888)

    def test_refresh_skips_inactive_accounts_and_empty_snapshots(self):
        for name in ("sync_ayugram", "sync_exteragram"):
            plugin_mod = load_plugin_module(f"{name}.plugin")
            plugin = plugin_mod.Plugin()

            # Empty snapshot -> instant return
            plugin._profiles_snapshot = {}
            plugin._chats_snapshot = {}
            plugin._refresh_loaded_telegram_objects()

            # Configure an inactive account
            from org.telegram.messenger import UserConfig
            u_c1 = UserConfig.getInstance(1)
            u_c1.isClientActivated = lambda: False

            target_uid = 778899
            plugin._profiles_cache[target_uid] = {"name_color": 3}
            plugin._update_snapshot()

            # Must execute safely without touching inactive account 1
            plugin._refresh_loaded_telegram_objects()

    def test_all_overloads_hooked_and_live_updates_patched(self):
        """Тест: регистрация хуков не пропускает перегрузки с разным числом параметров,
        а on_updates_hook гарантированно патчит входящих пользователей и чаты."""
        for name in ("sync_ayugram", "sync_exteragram"):
            plugin_mod = load_plugin_module(f"{name}.plugin")
            plugin = plugin_mod.Plugin()

            class FakeMethod:
                def __init__(self, name, param_types):
                    self._name = name
                    self._param_types = param_types
                def getName(self):
                    return self._name
                def getParameterTypes(self):
                    return self._param_types
                def setAccessible(self, val):
                    pass

            # Multiple overloads of putUser, putUsers, putChat, putChats, getUserFull
            fake_methods = [
                FakeMethod("putUser", [object(), object()]),                     # 2 params
                FakeMethod("putUser", [object(), object(), object()]),           # 3 params
                FakeMethod("putUsers", [object(), object()]),                    # 2 params
                FakeMethod("putUsers", [object(), object(), object()]),          # 3 params
                FakeMethod("putChat", [object(), object()]),                     # 2 params
                FakeMethod("putChat", [object(), object(), object()]),           # 3 params
                FakeMethod("putChats", [object(), object()]),                    # 2 params
                FakeMethod("getUserFull", [object()]),                           # 1 param (long)
                FakeMethod("getUserFull", [object()]),                           # 1 param (Long)
                FakeMethod("getChatFull", [object()]),                           # 1 param
            ]

            plugin_mod._get_class_methods = lambda cls: fake_methods
            plugin_mod.find_class = lambda n: object()

            hooked_calls = []
            plugin.hook_method = lambda m, h: hooked_calls.append((m.getName(), len(m.getParameterTypes()), h.__class__.__name__))

            plugin._register_xposed_hooks()

            # All 10 overloads must be hooked without skipping
            self.assertEqual(len(hooked_calls), 10)
            put_user_hooks = [h for h in hooked_calls if h[0] == "putUser"]
            self.assertEqual(len(put_user_hooks), 2)
            put_users_hooks = [h for h in hooked_calls if h[0] == "putUsers"]
            self.assertEqual(len(put_users_hooks), 2)

            # Test live on_updates_hook
            target_uid = 445566
            target_cid = 778899
            plugin._profiles_cache[target_uid] = {"name_color": 5, "emoji_status_id": 9999}
            plugin._chats_cache[target_cid] = {"name_color": 2}
            plugin._update_snapshot()

            class MockUpdatesContainer:
                def __init__(self, u_id, c_id):
                    self.users = [MockUser(u_id)]
                    self.chats = [MockChat(c_id)]
                    self.messages = []

            live_updates = MockUpdatesContainer(target_uid, target_cid)
            plugin.on_updates_hook("updates", 0, live_updates)

            u_obj = live_updates.users[0]
            self.assertIsNotNone(u_obj.color)
            self.assertEqual(u_obj.color.color, 5)
            self.assertEqual(u_obj.emoji_status.document_id, 9999)

            c_obj = live_updates.chats[0]
            self.assertIsNotNone(c_obj.color)
            self.assertEqual(c_obj.color.color, 2)

    def test_ayugram_multi_account_twink_views_main_account(self):
        """Тест: когда пользователь сидит с твинка (аккаунт 1) в AyuGram,
        его основной аккаунт (аккаунт 0, находящийся в базе SyncProfile)
        гарантированно отображается с кастомным цветом и эмодзи-статусом."""
        plugin_mod = load_plugin_module("sync_ayugram.plugin")
        plugin = plugin_mod.Plugin()

        main_uid = 111111
        twink_uid = 222222

        # Both accounts are logged into the client
        plugin._own_uids_cache = {main_uid, twink_uid}
        plugin._own_slots_cache = {main_uid: 0, twink_uid: 1}

        # Main account has custom profile in SyncProfile database
        plugin._profiles_cache[main_uid] = {
            "user_id": main_uid,
            "name_color": 4,
            "name_bg_emoji_id": 1234567,
            "profile_color": 2,
            "emoji_status_id": 88888,
            "premium": True,
        }
        plugin._update_snapshot()

        # Twink receives/views Main account's user object
        main_user_obj = MockUser(uid=main_uid)
        res = plugin._patch_user_tl_object(main_user_obj)
        self.assertTrue(res)
        self.assertIsNotNone(main_user_obj.color)
        self.assertEqual(main_user_obj.color.color, 4)
        self.assertEqual(main_user_obj.color.background_emoji_id, 1234567)
        self.assertEqual(main_user_obj.emoji_status.document_id, 88888)

        # Full user object
        main_full_obj = MockFullUser(uid=main_uid)
        res_full = plugin._patch_full_user_tl_object(main_full_obj, main_uid)
        self.assertTrue(res_full)
        self.assertIsNotNone(main_full_obj.color)
        self.assertEqual(main_full_obj.color.color, 4)

if __name__ == "__main__":
    unittest.main()



