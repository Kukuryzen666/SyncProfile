import asyncio
import json
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Dict, List, Optional
from android_utils import log as android_log, run_on_ui_thread
from base_plugin import BasePlugin, HookResult, HookStrategy, MenuItemData, MenuItemType, MethodHook
from hook_utils import find_class
from ui.bulletin import BulletinHelper
from ui.settings import Divider, Header, Input, Selector, Switch, Text
try:
    import zwylib
    from zwylib import async_manager, JsonCacheFile, build_log, build_bulletin_helper, HookUtils, UI, Localization, add_autoupdater_task, remove_autoupdater_task
    HAS_ZWYLIB = True
    logger = build_log('SyncProfile')
    bulletins = build_bulletin_helper('SyncProfile')
except Exception:
    HAS_ZWYLIB = False

    class _FallbackLog:

        def info(self, *args):
            android_log(f"SyncProfile: {' '.join((str(a) for a in args))}")

        def error(self, *args):
            android_log(f"SyncProfile [ERROR]: {' '.join((str(a) for a in args))}")

        def warning(self, *args):
            android_log(f"SyncProfile [WARN]: {' '.join((str(a) for a in args))}")

        def debug(self, *args):
            pass
    logger = _FallbackLog()

    class _FallbackBulletins:

        def show_info(self, message: str, fragment: Optional[Any]=None):
            run_on_ui_thread(lambda: BulletinHelper.show_info(message))

        def show_success(self, message: str, fragment: Optional[Any]=None):
            run_on_ui_thread(lambda: BulletinHelper.show_success(message))

        def show_error(self, message: str, fragment: Optional[Any]=None):
            run_on_ui_thread(lambda: BulletinHelper.show_error(message))

        def show_with_copy(self, message: str, text_to_copy: str, icon_res_id: int=0):
            run_on_ui_thread(lambda: BulletinHelper.show_copied_to_clipboard(f'{message}: {text_to_copy}'))
    bulletins = _FallbackBulletins()

def log(msg: Any):
    logger.info(str(msg))
__id__ = 'sync_profile'
__name__ = 'SyncProfile'
__description__ = 'Синхронизация кастомного профиля (цвета имени и реплаев, обложки, премиум эмодзи-статусы и фоновые узоры) между пользователями плагина с интеграцией ZwyLib.'
__author__ = '@Kukuryzen'
__version__ = '10.1.4'
__icon__ = 'exteraPlugins/1'
__app_version__ = '>=12.5.1'
__sdk_version__ = '>=1.4.3.3'
__requirements__ = []
DEFAULT_SERVER_URL = 'https://sync.efn.mom'
DEFAULT_SECRET_COOKIE = '36cbbc089c4c01bfbe97b33bdf431f63324e0ad0280b7166'
DEFAULT_NAME_BG_EMOJI = ''
DEFAULT_PROFILE_BG_EMOJI = ''
DEFAULT_EMOJI_STATUS_ID = ''
COOKIE_NAME = 'sync_access'
ALLOW_CUSTOM_SERVER_CONFIG = False
NAME_AND_REPLY_COLORS = ['0 - 🔵 Синий', '1 - 🟢 Зеленый', '2 - 🟠 Оранжевый', '3 - 🔴 Красный', '4 - 🟣 Фиолетовый', '5 - 🩵 Бирюзовый', '6 - 🌸 Розовый', '7 - 🔵 Синий диагональный', '8 - 🟢 Зеленый диагональный', '9 - 🟠 Оранжевый диагональный', '10 - 🔴 Красный диагональный', '11 - 🟣 Фиолетовый диагональный', '12 - 🩵 Бирюзовый диагональный', '13 - 🌸 Розовый диагональный', '14 - 🔵🔴 Сине-красный с ромбом', '15 - 🟠🟢 Оранжево-зеленый с ромбом', '16 - 🟢🔴 Зелено-красный с ромбом', '17 - 🩵🟢 Бирюзово-зеленый с ромбом', '18 - 🌊🌸 Морской-персиковый с ромбом', '19 - 🟣🟠 Фиолетово-оранжевый с ромбом', '20 - 🔵🟡 Сине-оранжевый с ромбом']
PROFILE_COLORS = ['0 - 🔵 Синий', '1 - 🟢 Зеленый', '2 - 🟠 Оранжевый', '3 - 🔴 Красный', '4 - 🟣 Фиолетовый', '5 - 🩵 Бирюзовый', '6 - 🌸 Розовый', '7 - ⚪ Серый', '8 - 🔵 Синий диагональный', '9 - 🟢 Зеленый диагональный', '10 - 🟠 Оранжевый диагональный', '11 - 🔴 Красный диагональный', '12 - 🟣 Фиолетовый диагональный', '13 - 🩵 Бирюзовый диагональный', '14 - 🌸 Розовый диагональный', '15 - ⚪ Серый диагональный']
PEER_COLOR_RGB_MAP = {0: -10443270, 1: -11870592, 2: -27392, 3: -306606, 4: -5745161, 5: -14494738, 6: -757066, 7: -10443270, 8: -11870592, 9: -27392, 10: -306606, 11: -5745161, 12: -14494738, 13: -757066, 14: -10443270, 15: -27392, 16: -11870592, 17: -14494738, 18: -14494738, 19: -5745161, 20: -10443270}

def _build_peer_color(color_id: int, bg_emoji_id: Any):
    from org.telegram.tgnet import TLRPC
    pc = TLRPC.TL_peerColor()
    c = int(color_id) if color_id is not None else 0
    if c < 0:
        c = 0
    pc.color = c
    bg = 0
    if bg_emoji_id is not None:
        try:
            bg_str = str(bg_emoji_id).strip()
            if bg_str and bg_str.isdigit():
                bg = int(bg_str)
        except Exception:
            bg = 0
    if bg != 0:
        pc.background_emoji_id = bg
        pc.flags = 3
    else:
        pc.background_emoji_id = 0
        pc.flags = 1
    return pc

class SyncProfilePlugin(BasePlugin):

    def __init__(self):
        super().__init__()
        self._profiles_cache: Dict[int, Dict[str, Any]] = {}
        self._pending_user_ids = set()
        self._unknown_uids_seen = set()
        self._batch_timer = None
        self._sync_lock = threading.Lock()
        self._cache_dirty = False
        self._is_running = True
        self._xposed_unhooks: List[Any] = []
        self._active_reply_rgb: int = 0
        self._json_cache_file = None
        if HAS_ZWYLIB:
            try:
                self._json_cache_file = JsonCacheFile('sync_profiles_cache.json', default={}, compress=True)
            except Exception as e:
                logger.error(f'Failed to init JsonCacheFile: {e}')

    def on_plugin_load(self):
        logger.info(f"SyncProfile v{__version__}: Загрузка (ZwyLib: {('Включен' if HAS_ZWYLIB else 'Не установлен')})...")
        self._is_running = True
        self._load_local_profiles_cache()
        self._auto_import_from_official_tg_premium()
        self._ensure_ayugram_premium()
        user_hooks = ['TL_users_getFullUser', 'TL_users_getUsers', 'TL_contacts_getContacts', 'TL_contacts_resolveUsername', 'TL_contacts_search', 'TL_photos_getUserPhotos', 'TL_messages_getMessages', 'TL_messages_getHistory', 'TL_messages_getDialogs', 'TL_messages_getPinnedDialogs', 'TL_messages_getDiscussionMessage', 'TL_messages_getChat', 'TL_messages_getFullChat', 'TL_messages_search', 'TL_messages_searchGlobal', 'TL_messages_getRecentLocations', 'TL_channels_getMessages', 'TL_channels_getParticipants', 'TL_channels_getParticipant', 'TL_channels_getChannels', 'TL_channels_getFullChannel', 'TL_updates_getDifference', 'TL_updates_getChannelDifference', 'TL_updates_getState', 'TL_help_getUserConfig', 'TL_help_getAppConfig', 'TL_account_getAuthorizations', 'TL_updates', 'TL_updatesCombined', 'TL_updateShort', 'TL_updateShortChatMessage', 'TL_updateShortMessage', 'TL_updateShortSentMessage', 'TL_updatesTooLong']
        for hook_name in user_hooks:
            try:
                self.add_hook(hook_name)
            except Exception as e:
                logger.warning(f'add_hook {hook_name} error: {e}')
        self._register_menu_items()
        self._register_xposed_hooks()
        self._apply_all_to_all_accounts()
        if HAS_ZWYLIB:
            async_manager.run_task(self._async_initial_background_sync())
            async_manager.run_task(self._async_keep_alive_sync_loop())
        else:
            threading.Thread(target=self._initial_background_sync, daemon=True).start()
            threading.Thread(target=self._keep_alive_sync_loop, daemon=True).start()
        logger.info(f'SyncProfile v{__version__}: Успешно загружен!')

    def on_plugin_unload(self):
        self._is_running = False
        with self._sync_lock:
            if self._batch_timer:
                try:
                    self._batch_timer.cancel()
                except Exception:
                    pass
                self._batch_timer = None
        if HAS_ZWYLIB:
            try:
                async_manager.cancel_all_for(__id__)
            except Exception:
                pass
        self._unregister_xposed_hooks()
        self._save_local_profiles_cache(force=True)
        logger.info(f'SyncProfile v{__version__}: Выгружен.')

    def _auto_import_from_official_tg_premium(self):
        imported_any = False
        try:
            from org.telegram.messenger import UserConfig
            max_accs = getattr(UserConfig, 'MAX_ACCOUNT_COUNT', 4)
            for acc in range(max_accs):
                try:
                    u_cfg = UserConfig.getInstance(acc)
                    if not u_cfg or not u_cfg.isClientActivated():
                        continue
                    try:
                        u_cfg.loadConfig()
                    except Exception:
                        pass
                    curr_user = u_cfg.getCurrentUser()
                    if not curr_user:
                        continue
                    is_real_premium = bool(getattr(curr_user, 'premium', False) or (getattr(curr_user, 'flags', 0) or 0) & 268435456 != 0)
                    has_official_color = hasattr(curr_user, 'color') and curr_user.color is not None
                    has_official_profile_color = hasattr(curr_user, 'profile_color') and curr_user.profile_color is not None
                    has_official_status = hasattr(curr_user, 'emoji_status') and curr_user.emoji_status is not None
                    if is_real_premium or has_official_color or has_official_profile_color or has_official_status:
                        if not self.get_setting(f'slot_{acc}_configured', False):
                            self._set_slot_val(acc, 'premium', True)
                            if has_official_color:
                                nc = int(getattr(curr_user.color, 'color', 2) or 0)
                                if nc >= 0:
                                    self._set_slot_val(acc, 'name_color', nc)
                                bg_em = getattr(curr_user.color, 'background_emoji_id', 0)
                                if bg_em != 0:
                                    self._set_slot_val(acc, 'name_bg_emoji_id', str(bg_em))
                            if has_official_profile_color:
                                prc = int(getattr(curr_user.profile_color, 'color', 2) or 0)
                                if prc >= 0:
                                    self._set_slot_val(acc, 'profile_color', prc)
                                p_bg_em = getattr(curr_user.profile_color, 'background_emoji_id', 0)
                                if p_bg_em != 0:
                                    self._set_slot_val(acc, 'profile_bg_emoji_id', str(p_bg_em))
                            if has_official_status:
                                doc_id = getattr(curr_user.emoji_status, 'document_id', 0)
                                if doc_id != 0:
                                    self._set_slot_val(acc, 'emoji_status_id', str(doc_id))
                            self.set_setting(f'slot_{acc}_configured', True, reload_settings=False)
                            imported_any = True
                            log(f'SyncProfile: Автоматически импортирован официальный TG Premium для аккаунта {acc + 1}')
                except Exception as e:
                    log(f'SyncProfile: Ошибка автоимпорта TG Premium для аккаунта {acc}: {e}')
        except Exception as e:
            log(f'SyncProfile: Ошибка автоимпорта: {e}')
        if imported_any:
            self._save_local_profiles_cache(force=True)
            self._apply_all_to_all_accounts()

    def _import_settings_from_current_account(self, acc_idx: int, show_bulletin: bool=True):
        try:
            from org.telegram.messenger import UserConfig
            u_cfg = UserConfig.getInstance(acc_idx)
            if not u_cfg or not u_cfg.isClientActivated():
                if show_bulletin:
                    run_on_ui_thread(lambda: BulletinHelper.show_error(f'Аккаунт {acc_idx + 1} не активирован.'))
                return
            try:
                u_cfg.loadConfig()
            except Exception:
                pass
            curr_user = u_cfg.getCurrentUser()
            if not curr_user:
                if show_bulletin:
                    run_on_ui_thread(lambda: BulletinHelper.show_error('Не удалось получить текущего пользователя.'))
                return
            nc = 0
            name_bg = ''
            prc = 0
            prof_bg = ''
            em_id = ''
            if hasattr(curr_user, 'color') and curr_user.color is not None:
                nc = int(getattr(curr_user.color, 'color', 0) or 0)
                bg_em = getattr(curr_user.color, 'background_emoji_id', 0)
                if bg_em != 0:
                    name_bg = str(bg_em)
            if hasattr(curr_user, 'profile_color') and curr_user.profile_color is not None:
                prc = int(getattr(curr_user.profile_color, 'color', 0) or 0)
                p_bg = getattr(curr_user.profile_color, 'background_emoji_id', 0)
                if p_bg != 0:
                    prof_bg = str(p_bg)
            if hasattr(curr_user, 'emoji_status') and curr_user.emoji_status is not None:
                doc_id = getattr(curr_user.emoji_status, 'document_id', 0)
                if doc_id != 0:
                    em_id = str(doc_id)
            self._set_slot_val(acc_idx, 'name_color', nc)
            self._set_slot_val(acc_idx, 'name_bg_emoji_id', name_bg)
            self._set_slot_val(acc_idx, 'profile_color', prc)
            self._set_slot_val(acc_idx, 'profile_bg_emoji_id', prof_bg)
            self._set_slot_val(acc_idx, 'emoji_status_id', em_id)
            self._set_slot_val(acc_idx, 'premium', True)
            self.set_setting(f'slot_{acc_idx}_configured', True, reload_settings=False)
            self._save_local_profiles_cache(force=True)
            self._apply_all_to_all_accounts()
            if show_bulletin:
                run_on_ui_thread(lambda: BulletinHelper.show_success(f"✨ Настройки успешно скопированы из Telegram!\nЦвет: #{nc} | Эмодзи: {name_bg or 'нет'}"))
        except Exception as e:
            log(f'SyncProfile: Ошибка ручного импорта: {e}')
            if show_bulletin:
                run_on_ui_thread(lambda: BulletinHelper.show_error(f'Ошибка импорта: {e}'))

    def _ensure_ayugram_premium(self):
        try:
            from com.radolyn.ayugram import AyuConfig
            if hasattr(AyuConfig, 'localPremium'):
                if self.get_setting('enable_local_premium', True):
                    AyuConfig.localPremium = True
                    if hasattr(AyuConfig, 'saveConfig'):
                        AyuConfig.saveConfig()
                    elif hasattr(AyuConfig, 'save'):
                        AyuConfig.save()
        except Exception:
            pass
        try:
            from com.exteragram.messenger import ExteraConfig
            if hasattr(ExteraConfig, 'localPremium'):
                if self.get_setting('enable_local_premium', True):
                    ExteraConfig.localPremium = True
        except Exception:
            pass
        try:
            from org.telegram.messenger import UserConfig
            for acc in range(4):
                try:
                    u_cfg = UserConfig.getInstance(acc)
                    if u_cfg and hasattr(u_cfg, 'isPremium'):
                        u_cfg.isPremium = True
                    if u_cfg and hasattr(u_cfg, 'getCurrentUser'):
                        curr_u = u_cfg.getCurrentUser()
                        if curr_u:
                            curr_u.premium = True
                            curr_u.flags = int(getattr(curr_u, 'flags', 0) | 268435456)
                            curr_u.flags2 = int(getattr(curr_u, 'flags2', 0) | 2)
                except Exception:
                    pass
        except Exception:
            pass

    def _on_local_premium_toggle(self, enabled: bool):
        try:
            from com.radolyn.ayugram import AyuConfig
            if hasattr(AyuConfig, 'localPremium'):
                AyuConfig.localPremium = bool(enabled)
                if hasattr(AyuConfig, 'saveConfig'):
                    AyuConfig.saveConfig()
                elif hasattr(AyuConfig, 'save'):
                    AyuConfig.save()
        except Exception:
            pass
        try:
            from com.exteragram.messenger import ExteraConfig
            if hasattr(ExteraConfig, 'localPremium'):
                ExteraConfig.localPremium = bool(enabled)
        except Exception:
            pass
        self._apply_all_to_all_accounts()

    def _get_my_active_uids(self) -> List[int]:
        uids = []
        try:
            from org.telegram.messenger import UserConfig
            for acc in range(4):
                try:
                    u_c = UserConfig.getInstance(acc)
                    if u_c and u_c.isClientActivated():
                        uid = int(u_c.getClientUserId() or 0)
                        if uid != 0 and uid not in uids:
                            uids.append(uid)
                except Exception:
                    pass
        except Exception:
            pass
        return uids

    def _get_active_accounts_data(self) -> List[Dict[str, Any]]:
        accounts = []
        try:
            from org.telegram.messenger import UserConfig
            selected = getattr(UserConfig, 'selectedAccount', 0)
            max_accs = getattr(UserConfig, 'MAX_ACCOUNT_COUNT', 4)
            for acc in range(max_accs):
                try:
                    u_cfg = UserConfig.getInstance(acc)
                    if not u_cfg:
                        continue
                    try:
                        u_cfg.loadConfig()
                    except Exception:
                        pass
                    is_active = bool(u_cfg.isClientActivated())
                    curr_user = u_cfg.getCurrentUser()
                    uid = int(u_cfg.getClientUserId() or (getattr(curr_user, 'id', 0) if curr_user else 0))
                    if is_active and uid > 0 and (curr_user is not None):
                        fn = str(getattr(curr_user, 'first_name', '') or '')
                        ln = str(getattr(curr_user, 'last_name', '') or '')
                        uname = str(getattr(curr_user, 'username', '') or '')
                        phone = str(getattr(curr_user, 'phone', '') or '')
                        name = ' '.join([p for p in [fn, ln] if p]).strip() or f'Аккаунт {acc + 1}'
                        extra = f'@{uname}' if uname else phone
                        extra_str = f' ({extra})' if extra else ''
                        is_curr = acc == selected
                        accounts.append({'acc_idx': acc, 'user_id': uid, 'name': name, 'extra': extra_str, 'is_current': is_curr})
                except Exception:
                    pass
        except Exception:
            pass
        if not accounts:
            try:
                from org.telegram.messenger import UserConfig
                curr_user = UserConfig.getInstance(UserConfig.selectedAccount).getCurrentUser()
                uid = int(UserConfig.getInstance(UserConfig.selectedAccount).getClientUserId() or (getattr(curr_user, 'id', 0) if curr_user else 0))
                if uid > 0:
                    fn = str(getattr(curr_user, 'first_name', '') or '') if curr_user else ''
                    ln = str(getattr(curr_user, 'last_name', '') or '') if curr_user else ''
                    uname = str(getattr(curr_user, 'username', '') or '') if curr_user else ''
                    name = ' '.join([p for p in [fn, ln] if p]).strip() or 'Мой аккаунт'
                    extra = f' (@{uname})' if uname else ''
                    accounts.append({'acc_idx': UserConfig.selectedAccount, 'user_id': uid, 'name': name, 'extra': extra, 'is_current': True})
            except Exception:
                pass
        accounts.sort(key=lambda x: x['acc_idx'])
        return accounts

    def _get_slot_val(self, acc_idx: int, key: str, default: Any) -> Any:
        slot_key = f'slot_{acc_idx}_{key}'
        val = self.get_setting(slot_key, None)
        if val is not None and str(val).strip() != '':
            return val
        if acc_idx == 0:
            legacy_val = self.get_setting(f'my_{key}', None)
            if legacy_val is not None and str(legacy_val).strip() != '':
                return legacy_val
        return default

    def _set_slot_val(self, acc_idx: int, key: str, val: Any):
        slot_key = f'slot_{acc_idx}_{key}'
        self.set_setting(slot_key, val)
        self.set_setting(f'slot_{acc_idx}_configured', True, reload_settings=False)
        if acc_idx == 0:
            self.set_setting(f'my_{key}', val)

    def _get_profile_dict_for_slot(self, acc_idx: int, user_id: int) -> Dict[str, Any]:
        default_name_c = 0
        default_prof_c = 0
        name_c = int(self._get_slot_val(acc_idx, 'name_color', default_name_c) or 0)
        if name_c < 0:
            name_c = 0
        name_bg_str = str(self._get_slot_val(acc_idx, 'name_bg_emoji_id', DEFAULT_NAME_BG_EMOJI) or '').strip()
        name_bg = int(name_bg_str) if name_bg_str and name_bg_str.isdigit() and (int(name_bg_str) != 0) else 0
        prof_c = int(self._get_slot_val(acc_idx, 'profile_color', default_prof_c) or 0)
        if prof_c < 0:
            prof_c = 0
        prof_bg_str = str(self._get_slot_val(acc_idx, 'profile_bg_emoji_id', DEFAULT_PROFILE_BG_EMOJI) or '').strip()
        prof_bg = int(prof_bg_str) if prof_bg_str and prof_bg_str.isdigit() and (int(prof_bg_str) != 0) else 0
        em_str = str(self._get_slot_val(acc_idx, 'emoji_status_id', DEFAULT_EMOJI_STATUS_ID) or '').strip()
        em_id = int(em_str) if em_str and em_str.isdigit() and (int(em_str) != 0) else 0
        prem = bool(self._get_slot_val(acc_idx, 'premium', True))
        return {'user_id': user_id, 'premium': prem, 'emoji_status_id': em_id, 'name_color': name_c, 'name_bg_emoji_id': name_bg, 'profile_color': prof_c, 'profile_bg_emoji_id': prof_bg, 'client_type': 'AyuGram', 'auth_key': self.get_setting('auth_key', '').strip()}

    def get_cached_profile(self, uid: int) -> Optional[Dict[str, Any]]:
        if not uid or uid <= 0:
            return None
        with self._sync_lock:
            return self._profiles_cache.get(uid)

    def _get_vibrant_color_for_id(self, color_id: int) -> int:
        c = int(color_id) if color_id is not None else 2
        if c < 0 or c not in PEER_COLOR_RGB_MAP:
            c = abs(c) % 7 if c >= 0 else 2
        return PEER_COLOR_RGB_MAP.get(c, -7461718)

    def _get_peer_color_object(self, acc: int, color_id: int, is_profile: bool=False):
        try:
            from org.telegram.messenger import MessagesController
            mc = MessagesController.getInstance(acc)
            if mc:
                pcs = mc.getProfilePeerColors() if is_profile else mc.getPeerColors()
                if pcs and hasattr(pcs, 'getColor'):
                    pc = pcs.getColor(color_id)
                    if pc:
                        return pc
                if hasattr(mc, 'getPeerColor'):
                    pc = mc.getPeerColor(color_id)
                    if pc:
                        return pc
        except Exception:
            pass
        return None

    def _resolve_color_id_for_user(self, user_or_uid: Any) -> int:
        if not user_or_uid:
            return 0
        uid = int(getattr(user_or_uid, 'id', user_or_uid) or 0) if not isinstance(user_or_uid, int) else user_or_uid
        if uid > 0:
            prof = self.get_cached_profile(uid)
            if prof:
                return int(prof.get('name_color', 0) or 0)
        if hasattr(user_or_uid, 'color'):
            c = getattr(user_or_uid, 'color', None)
            if c and hasattr(c, 'color'):
                return int(c.color)
        if uid > 0:
            return int(abs(uid) % 7)
        return 0

    def _resolve_emoji_id_for_user(self, user_or_uid: Any) -> int:
        if not user_or_uid:
            return 0
        uid = int(getattr(user_or_uid, 'id', user_or_uid) or 0) if not isinstance(user_or_uid, int) else user_or_uid
        if uid > 0:
            prof = self.get_cached_profile(uid)
            if prof and prof.get('name_bg_emoji_id'):
                try:
                    val = int(prof['name_bg_emoji_id'])
                    if val != 0:
                        return val
                except Exception:
                    pass
            try:
                from org.telegram.messenger import UserConfig
                max_accs = getattr(UserConfig, 'MAX_ACCOUNT_COUNT', 4)
                for a in range(max_accs):
                    u_c = UserConfig.getInstance(a)
                    if u_c and int(u_c.getClientUserId() or 0) == uid:
                        slot_bg = str(self._get_slot_val(a, 'name_bg_emoji_id', '') or '').strip()
                        if slot_bg and slot_bg.isdigit() and (int(slot_bg) != 0):
                            return int(slot_bg)
            except Exception:
                pass
        if hasattr(user_or_uid, 'color'):
            c = getattr(user_or_uid, 'color', None)
            if c and hasattr(c, 'background_emoji_id'):
                try:
                    val = int(c.background_emoji_id or 0)
                    if val != 0:
                        return val
                except Exception:
                    pass
        try:
            from com.radolyn.ayugram import AyuConfig
            if hasattr(AyuConfig, 'nameCustomEmojiId') and AyuConfig.nameCustomEmojiId:
                val_str = str(AyuConfig.nameCustomEmojiId).strip()
                if val_str and val_str.isdigit() and (int(val_str) != 0):
                    return int(val_str)
        except Exception:
            pass
        return 0

    def _extract_reply_uid(self, msg: Any) -> int:
        if not msg:
            return 0
        try:
            r_msg = getattr(msg, 'replyMessageObject', None)
            if r_msg:
                try:
                    if hasattr(r_msg, 'getDialogId'):
                        d_id = int(r_msg.getDialogId() or 0)
                        if d_id > 0:
                            return d_id
                except Exception:
                    pass
                peer = getattr(r_msg, 'getFromPeer', lambda: None)()
                if peer:
                    uid = self._extract_peer_uid(peer)
                    if uid > 0:
                        return uid
                mo = getattr(r_msg, 'messageOwner', None)
                if mo:
                    uid = self._extract_peer_uid(getattr(mo, 'from_id', None))
                    if uid > 0:
                        return uid
                    uid = self._extract_peer_uid(getattr(mo, 'peer_id', None))
                    if uid > 0:
                        return uid
            if hasattr(msg, 'getReplyDialogId'):
                try:
                    d_id = int(msg.getReplyDialogId() or 0)
                    if d_id > 0:
                        return d_id
                except Exception:
                    pass
            mo = getattr(msg, 'messageOwner', None)
            if mo:
                r_to = getattr(mo, 'reply_to', None)
                if r_to:
                    uid = self._extract_peer_uid(getattr(r_to, 'reply_to_peer_id', None))
                    if uid > 0:
                        return uid
                    r_from = getattr(r_to, 'reply_from', None)
                    if r_from:
                        uid = self._extract_peer_uid(getattr(r_from, 'from_id', None))
                        if uid > 0:
                            return uid
                        uid = self._extract_peer_uid(getattr(r_from, 'peer_id', None))
                        if uid > 0:
                            return uid
            r_to = getattr(msg, 'reply_to', None)
            if r_to:
                uid = self._extract_peer_uid(getattr(r_to, 'reply_to_peer_id', None))
                if uid > 0:
                    return uid
            has_reply = bool(getattr(msg, 'replyMessageObject', None) or (mo and getattr(mo, 'reply_to', None)) or getattr(msg, 'reply_to', None))
            if has_reply:
                dialog_id = 0
                if hasattr(msg, 'getDialogId'):
                    try:
                        dialog_id = int(msg.getDialogId() or 0)
                    except Exception:
                        pass
                if dialog_id == 0 and mo:
                    peer_id = getattr(mo, 'peer_id', None)
                    if peer_id:
                        dialog_id = self._extract_peer_uid(peer_id)
                if dialog_id > 0:
                    is_out = bool(getattr(msg, 'isOut', lambda: False)() or (mo and getattr(mo, 'out', False)) or getattr(msg, 'out', False))
                    if is_out:
                        return dialog_id
                    else:
                        try:
                            acc = getattr(msg, 'currentAccount', 0)
                            from org.telegram.messenger import UserConfig
                            u_c = UserConfig.getInstance(acc)
                            if u_c:
                                my_id = int(u_c.getClientUserId() or 0)
                                if my_id > 0:
                                    return my_id
                        except Exception:
                            pass
        except Exception:
            pass
        return 0

    def _register_xposed_hooks(self):
        try:
            MessagesControllerClass = find_class('org.telegram.messenger.MessagesController')
            PeerColorsClass = find_class('org.telegram.messenger.MessagesController$PeerColors')
            PeerColorClass = find_class('org.telegram.messenger.MessagesController$PeerColor')
            MessagesStorageClass = find_class('org.telegram.messenger.MessagesStorage')
            UserObjectClass = find_class('org.telegram.messenger.UserObject')
            MessageObjectClass = find_class('org.telegram.messenger.MessageObject')
            ChatMessageCellClass = find_class('org.telegram.ui.Cells.ChatMessageCell')
            ThemeClass = find_class('org.telegram.ui.ActionBar.Theme')
            UserConfigClass = find_class('org.telegram.messenger.UserConfig')
            plugin_self = self
            if ThemeClass:

                class ThemeGetColorHook(MethodHook):

                    def after_hooked_method(self, param):
                        try:
                            if plugin_self._active_reply_rgb != 0:
                                args = getattr(param, 'args', None)
                                if args and len(args) > 0 and isinstance(args[0], str):
                                    key = args[0]
                                    if key in ('chat_outReplyNameText', 'chat_outReplyLine', 'chat_inReplyNameText', 'chat_inReplyLine', 'chat_replyNameText', 'chat_replyLine', 'chat_outReplyMedia', 'chat_inReplyMedia'):
                                        param.setResult(plugin_self._active_reply_rgb)
                        except Exception:
                            pass
                for m in ThemeClass.getDeclaredMethods():
                    try:
                        m_name = m.getName()
                        if m_name in ('getColor', 'getThemeColor'):
                            m.setAccessible(True)
                            un = self.hook_method(m, ThemeGetColorHook())
                            if un:
                                self._xposed_unhooks.append(un)
                    except Exception as e:
                        log(f'SyncProfile: hook Theme method error: {e}')
            if PeerColorClass:

                class PeerColorGetColorHook(MethodHook):

                    def after_hooked_method(self, param):
                        try:
                            this_pc = getattr(param, 'thisObject', None)
                            if this_pc:
                                color_id = getattr(this_pc, 'id', None)
                                if color_id is None:
                                    color_id = getattr(this_pc, 'color', 0)
                                vibrant = plugin_self._get_vibrant_color_for_id(color_id)
                                param.setResult(vibrant)
                        except Exception:
                            pass
                for m in PeerColorClass.getDeclaredMethods():
                    try:
                        m_name = m.getName()
                        if m_name in ('getColor', 'getBgColor', 'getColor1', 'getColor2', 'getColor3', 'getColor4'):
                            m.setAccessible(True)
                            un = self.hook_method(m, PeerColorGetColorHook())
                            if un:
                                self._xposed_unhooks.append(un)
                    except Exception as e:
                        log(f'SyncProfile: hook PeerColor method error: {e}')
            if PeerColorsClass and PeerColorClass:

                class PeerColorsGetColorHook(MethodHook):

                    def after_hooked_method(self, param):
                        try:
                            res = param.getResult()
                            if res is None:
                                args = getattr(param, 'args', None)
                                c_id = args[0] if args and len(args) > 0 and isinstance(args[0], int) else 0
                                this_pcs = getattr(param, 'thisObject', None)
                                if this_pcs and hasattr(this_pcs, 'colors'):
                                    colors_list = getattr(this_pcs, 'colors', None)
                                    if colors_list and colors_list.size() > 0:
                                        param.setResult(colors_list.get(c_id % colors_list.size()))
                        except Exception:
                            pass
                for m in PeerColorsClass.getDeclaredMethods():
                    try:
                        if m.getName() == 'getColor':
                            m.setAccessible(True)
                            un = self.hook_method(m, PeerColorsGetColorHook())
                            if un:
                                self._xposed_unhooks.append(un)
                    except Exception as e:
                        log(f'SyncProfile: hook PeerColors.getColor error: {e}')
            if ChatMessageCellClass:

                def _apply_cell_reply_color(cell, msg, is_draw_phase: bool=False):
                    if not cell or not msg:
                        return
                    try:
                        r_uid = plugin_self._extract_reply_uid(msg)
                        if r_uid > 0:
                            plugin_self._queue_fetch_user(r_uid)
                            nc = plugin_self._resolve_color_id_for_user(r_uid)
                            bg_em = plugin_self._resolve_emoji_id_for_user(r_uid)
                            vibrant_rgb = plugin_self._get_vibrant_color_for_id(nc)
                            try:
                                mo = getattr(msg, 'messageOwner', None)
                                if mo and hasattr(mo, 'reply_to') and mo.reply_to:
                                    if bg_em != 0:
                                        mo.reply_to.background_emoji_id = bg_em
                                        flags = getattr(mo.reply_to, 'flags', 0) or 0
                                        mo.reply_to.flags = flags | 128
                                r_msg = getattr(msg, 'replyMessageObject', None)
                                if r_msg:
                                    r_msg._sync_bg_emoji_id = bg_em
                                    r_msg._sync_color_id = nc
                                    r_mo = getattr(r_msg, 'messageOwner', None)
                                    if r_mo:
                                        if bg_em != 0 and hasattr(r_mo, 'color') and r_mo.color:
                                            r_mo.color.background_emoji_id = bg_em
                            except Exception:
                                pass
                        else:
                            vibrant_rgb = 0
                        try:
                            msg._sync_reply_rgb = vibrant_rgb
                        except Exception:
                            pass
                        if not vibrant_rgb or vibrant_rgb == 0:
                            return
                        plugin_self._active_reply_rgb = vibrant_rgb
                        for field_name in ('replyNamePaint', 'replyLinePaint', 'quotePaint', 'replyLine'):
                            try:
                                f_paint = getattr(cell, field_name, None)
                                if f_paint and hasattr(f_paint, 'setColor'):
                                    f_paint.setColor(vibrant_rgb)
                            except Exception:
                                pass
                        try:
                            if hasattr(cell, 'replyNameColor'):
                                cell.replyNameColor = vibrant_rgb
                            if hasattr(cell, 'replyLineColor'):
                                cell.replyLineColor = vibrant_rgb
                        except Exception:
                            pass
                        try:
                            r_layout = getattr(cell, 'replyNameLayout', None)
                            if r_layout and hasattr(r_layout, 'getPaint'):
                                lp = r_layout.getPaint()
                                if lp and hasattr(lp, 'setColor'):
                                    lp.setColor(vibrant_rgb)
                        except Exception:
                            pass
                        if ThemeClass:
                            for theme_paint in ('chat_replyNameTextPaint', 'chat_replyLinePaint', 'chat_quoteLinePaint', 'chat_outReplyNameTextPaint', 'chat_outReplyLinePaint', 'chat_inReplyNameTextPaint', 'chat_inReplyLinePaint'):
                                try:
                                    tp = getattr(ThemeClass, theme_paint, None)
                                    if tp and hasattr(tp, 'setColor'):
                                        tp.setColor(vibrant_rgb)
                                except Exception:
                                    pass
                    except Exception:
                        pass

                class ChatMessageCellDrawHook(MethodHook):

                    def before_hooked_method(self, param):
                        try:
                            cell = getattr(param, 'thisObject', None)
                            if cell:
                                msg = getattr(cell, 'currentMessageObject', None)
                                _apply_cell_reply_color(cell, msg, is_draw_phase=True)
                        except Exception:
                            pass

                    def after_hooked_method(self, param):
                        plugin_self._active_reply_rgb = 0

                class ChatMessageCellSetMsgHook(MethodHook):

                    def before_hooked_method(self, param):
                        try:
                            cell = getattr(param, 'thisObject', None)
                            if cell:
                                args = getattr(param, 'args', None)
                                msg = args[0] if args and len(args) > 0 else getattr(cell, 'currentMessageObject', None)
                                _apply_cell_reply_color(cell, msg, is_draw_phase=False)
                        except Exception:
                            pass

                    def after_hooked_method(self, param):
                        try:
                            cell = getattr(param, 'thisObject', None)
                            if cell:
                                args = getattr(param, 'args', None)
                                msg = args[0] if args and len(args) > 0 else getattr(cell, 'currentMessageObject', None)
                                _apply_cell_reply_color(cell, msg, is_draw_phase=False)
                            plugin_self._active_reply_rgb = 0
                        except Exception:
                            pass
                for m in ChatMessageCellClass.getDeclaredMethods():
                    try:
                        m_name = m.getName()
                        if m_name in ('onDraw', 'draw', 'dispatchDraw', 'drawReply', 'drawQuote', 'drawReplyText'):
                            m.setAccessible(True)
                            un = self.hook_method(m, ChatMessageCellDrawHook())
                            if un:
                                self._xposed_unhooks.append(un)
                        elif m_name in ('setMessageObject', 'createReplyLayout', 'buildReplyLayout', 'checkReplyLayout'):
                            m.setAccessible(True)
                            un = self.hook_method(m, ChatMessageCellSetMsgHook())
                            if un:
                                self._xposed_unhooks.append(un)
                    except Exception as e:
                        log(f'SyncProfile: hook ChatMessageCell method {m} error: {e}')
            if UserConfigClass:

                class UserConfigIsPremiumHook(MethodHook):

                    def after_hooked_method(self, param):
                        try:
                            if plugin_self.get_setting('enable_local_premium', True):
                                param.setResult(True)
                        except Exception:
                            pass
                for m in UserConfigClass.getDeclaredMethods():
                    try:
                        m_name = m.getName()
                        if m_name in ('isPremium', 'hasPremiumOnAccounts', 'hasPremium'):
                            m.setAccessible(True)
                            un = self.hook_method(m, UserConfigIsPremiumHook())
                            if un:
                                self._xposed_unhooks.append(un)
                    except Exception as e:
                        log(f'SyncProfile: hook UserConfig method {m} error: {e}')
            if UserObjectClass:

                class IsPremiumUserHook(MethodHook):

                    def after_hooked_method(self, param):
                        try:
                            if plugin_self.get_setting('enable_local_premium', True):
                                param.setResult(True)
                        except Exception:
                            pass

                class GetColorIdHook(MethodHook):

                    def after_hooked_method(self, param):
                        try:
                            args = getattr(param, 'args', None)
                            if args and len(args) > 0 and hasattr(args[0], 'id'):
                                u = args[0]
                                c_id = plugin_self._resolve_color_id_for_user(u)
                                param.setResult(c_id)
                        except Exception:
                            pass

                class GetEmojiIdHook(MethodHook):

                    def after_hooked_method(self, param):
                        try:
                            args = getattr(param, 'args', None)
                            if args and len(args) > 0 and hasattr(args[0], 'id'):
                                uid = int(getattr(args[0], 'id', 0) or 0)
                                if uid > 0:
                                    prof = plugin_self.get_cached_profile(uid)
                                    if prof and prof.get('name_bg_emoji_id'):
                                        param.setResult(int(prof['name_bg_emoji_id']))
                        except Exception:
                            pass

                class GetProfileColorIdHook(MethodHook):

                    def after_hooked_method(self, param):
                        try:
                            args = getattr(param, 'args', None)
                            if args and len(args) > 0 and hasattr(args[0], 'id'):
                                uid = int(getattr(args[0], 'id', 0) or 0)
                                if uid > 0:
                                    prof = plugin_self.get_cached_profile(uid)
                                    if prof:
                                        param.setResult(int(prof.get('profile_color', 0) or 0))
                        except Exception:
                            pass

                class GetProfileEmojiIdHook(MethodHook):

                    def after_hooked_method(self, param):
                        try:
                            args = getattr(param, 'args', None)
                            if args and len(args) > 0 and hasattr(args[0], 'id'):
                                uid = int(getattr(args[0], 'id', 0) or 0)
                                if uid > 0:
                                    prof = plugin_self.get_cached_profile(uid)
                                    if prof and prof.get('profile_bg_emoji_id'):
                                        param.setResult(int(prof['profile_bg_emoji_id']))
                        except Exception:
                            pass

                class HasColorHook(MethodHook):

                    def after_hooked_method(self, param):
                        param.setResult(True)

                class GetPeerColorForUserHook(MethodHook):

                    def after_hooked_method(self, param):
                        try:
                            args = getattr(param, 'args', None)
                            if args:
                                user = None
                                acc = 0
                                for arg in args:
                                    if isinstance(arg, int):
                                        acc = arg
                                    elif hasattr(arg, 'id'):
                                        user = arg
                                if user:
                                    c_id = plugin_self._resolve_color_id_for_user(user)
                                    pc = plugin_self._get_peer_color_object(acc, c_id, is_profile=False)
                                    if pc:
                                        param.setResult(pc)
                        except Exception:
                            pass

                uo_methods = UserObjectClass.getDeclaredMethods()
                for m in uo_methods:
                    try:
                        m_name = m.getName()
                        if m_name in ('isPremiumUser', 'isPremium', 'hasPremium'):
                            m.setAccessible(True)
                            un = self.hook_method(m, IsPremiumUserHook())
                            if un:
                                self._xposed_unhooks.append(un)
                        elif m_name == 'getColorId':
                            m.setAccessible(True)
                            un = self.hook_method(m, GetColorIdHook())
                            if un:
                                self._xposed_unhooks.append(un)
                        elif m_name == 'getEmojiId':
                            m.setAccessible(True)
                            un = self.hook_method(m, GetEmojiIdHook())
                            if un:
                                self._xposed_unhooks.append(un)
                        elif m_name == 'getProfileColorId':
                            m.setAccessible(True)
                            un = self.hook_method(m, GetProfileColorIdHook())
                            if un:
                                self._xposed_unhooks.append(un)
                        elif m_name == 'getProfileEmojiId':
                            m.setAccessible(True)
                            un = self.hook_method(m, GetProfileEmojiIdHook())
                            if un:
                                self._xposed_unhooks.append(un)
                        elif m_name == 'hasColor':
                            m.setAccessible(True)
                            un = self.hook_method(m, HasColorHook())
                            if un:
                                self._xposed_unhooks.append(un)
                        elif m_name == 'getPeerColorForUser':
                            m.setAccessible(True)
                            un = self.hook_method(m, GetPeerColorForUserHook())
                            if un:
                                self._xposed_unhooks.append(un)

                    except Exception as e:
                        log(f'SyncProfile: hook UserObject method {m} error: {e}')
            if MessageObjectClass:

                class MsgObjGetColorIdHook(MethodHook):

                    def after_hooked_method(self, param):
                        try:
                            msg_obj = getattr(param, 'thisObject', None)
                            if msg_obj:
                                uid = 0
                                peer = getattr(msg_obj, 'getFromPeer', lambda: None)()
                                if peer:
                                    uid = plugin_self._extract_peer_uid(peer)
                                if uid == 0:
                                    uid = int(getattr(msg_obj, 'getDialogId', lambda: 0)() or 0)
                                if uid == 0:
                                    mo = getattr(msg_obj, 'messageOwner', None)
                                    if mo:
                                        uid = plugin_self._extract_peer_uid(getattr(mo, 'from_id', None))
                                if uid > 0:
                                    c_id = plugin_self._resolve_color_id_for_user(uid)
                                    param.setResult(c_id)
                        except Exception:
                            pass

                class MsgObjGetReplyColorIdHook(MethodHook):

                    def after_hooked_method(self, param):
                        try:
                            msg_obj = getattr(param, 'thisObject', None)
                            if msg_obj:
                                r_uid = plugin_self._extract_reply_uid(msg_obj)
                                if r_uid > 0:
                                    c_id = plugin_self._resolve_color_id_for_user(r_uid)
                                    param.setResult(c_id)
                        except Exception:
                            pass

                class MsgObjGetEmojiIdHook(MethodHook):

                    def after_hooked_method(self, param):
                        try:
                            msg_obj = getattr(param, 'thisObject', None)
                            if msg_obj:
                                uid = 0
                                peer = getattr(msg_obj, 'getFromPeer', lambda: None)()
                                if peer:
                                    uid = plugin_self._extract_peer_uid(peer)
                                if uid == 0:
                                    uid = int(getattr(msg_obj, 'getDialogId', lambda: 0)() or 0)
                                if uid > 0:
                                    em_id = plugin_self._resolve_emoji_id_for_user(uid)
                                    if em_id != 0:
                                        param.setResult(em_id)
                        except Exception:
                            pass

                class MsgObjGetReplyEmojiIdHook(MethodHook):

                    def after_hooked_method(self, param):
                        try:
                            msg_obj = getattr(param, 'thisObject', None)
                            if msg_obj:
                                r_uid = plugin_self._extract_reply_uid(msg_obj)
                                if r_uid > 0:
                                    em_id = plugin_self._resolve_emoji_id_for_user(r_uid)
                                    if em_id != 0:
                                        param.setResult(em_id)
                        except Exception:
                            pass

                class MsgObjHasEmojiHook(MethodHook):

                    def after_hooked_method(self, param):
                        try:
                            msg_obj = getattr(param, 'thisObject', None)
                            if msg_obj:
                                uid = 0
                                peer = getattr(msg_obj, 'getFromPeer', lambda: None)()
                                if peer:
                                    uid = plugin_self._extract_peer_uid(peer)
                                if uid == 0:
                                    uid = int(getattr(msg_obj, 'getDialogId', lambda: 0)() or 0)
                                if uid > 0:
                                    em_id = plugin_self._resolve_emoji_id_for_user(uid)
                                    if em_id != 0:
                                        param.setResult(True)
                        except Exception:
                            pass

                class MsgObjHasReplyEmojiHook(MethodHook):

                    def after_hooked_method(self, param):
                        try:
                            msg_obj = getattr(param, 'thisObject', None)
                            if msg_obj:
                                r_uid = plugin_self._extract_reply_uid(msg_obj)
                                if r_uid > 0:
                                    em_id = plugin_self._resolve_emoji_id_for_user(r_uid)
                                    if em_id != 0:
                                        param.setResult(True)
                        except Exception:
                            pass

                class MsgObjGetPeerColorHook(MethodHook):

                    def after_hooked_method(self, param):
                        try:
                            msg_obj = getattr(param, 'thisObject', None)
                            if msg_obj:
                                uid = 0
                                peer = getattr(msg_obj, 'getFromPeer', lambda: None)()
                                if peer:
                                    uid = plugin_self._extract_peer_uid(peer)
                                if uid == 0:
                                    uid = int(getattr(msg_obj, 'getDialogId', lambda: 0)() or 0)
                                if uid > 0:
                                    nc = plugin_self._resolve_color_id_for_user(uid)
                                    acc = getattr(msg_obj, 'currentAccount', 0)
                                    pc = plugin_self._get_peer_color_object(acc, nc, is_profile=False)
                                    if pc:
                                        param.setResult(pc)
                        except Exception:
                            pass

                class MsgObjGetReplyPeerColorHook(MethodHook):

                    def after_hooked_method(self, param):
                        try:
                            msg_obj = getattr(param, 'thisObject', None)
                            if msg_obj:
                                r_uid = plugin_self._extract_reply_uid(msg_obj)
                                if r_uid > 0:
                                    nc = plugin_self._resolve_color_id_for_user(r_uid)
                                    acc = getattr(msg_obj, 'currentAccount', 0)
                                    pc = plugin_self._get_peer_color_object(acc, nc, is_profile=False)
                                    if pc:
                                        param.setResult(pc)
                        except Exception:
                            pass

                class MsgObjGetReplyColorHook(MethodHook):

                    def after_hooked_method(self, param):
                        try:
                            msg_obj = getattr(param, 'thisObject', None)
                            if msg_obj:
                                r_uid = plugin_self._extract_reply_uid(msg_obj)
                                if r_uid > 0:
                                    nc = plugin_self._resolve_color_id_for_user(r_uid)
                                    param.setResult(plugin_self._get_vibrant_color_for_id(nc))
                        except Exception:
                            pass
                for m in MessageObjectClass.getDeclaredMethods():
                    try:
                        m_name = m.getName()
                        p_count = len(m.getParameterTypes())
                        if m_name == 'getColorId' and p_count == 0:
                            m.setAccessible(True)
                            un = self.hook_method(m, MsgObjGetColorIdHook())
                            if un:
                                self._xposed_unhooks.append(un)
                        elif m_name == 'getReplyColorId' and p_count == 0:
                            m.setAccessible(True)
                            un = self.hook_method(m, MsgObjGetReplyColorIdHook())
                            if un:
                                self._xposed_unhooks.append(un)
                        elif m_name in ('getEmojiId', 'getBackgroundEmojiId', 'getPatternEmojiId') and p_count == 0:
                            m.setAccessible(True)
                            un = self.hook_method(m, MsgObjGetEmojiIdHook())
                            if un:
                                self._xposed_unhooks.append(un)
                        elif m_name in ('getReplyEmojiId', 'getReplyBackgroundEmojiId', 'getReplyPatternEmojiId') and p_count == 0:
                            m.setAccessible(True)
                            un = self.hook_method(m, MsgObjGetReplyEmojiIdHook())
                            if un:
                                self._xposed_unhooks.append(un)
                        elif m_name in ('hasEmoji', 'hasBackgroundEmoji', 'hasPatternEmoji') and p_count == 0:
                            m.setAccessible(True)
                            un = self.hook_method(m, MsgObjHasEmojiHook())
                            if un:
                                self._xposed_unhooks.append(un)
                        elif m_name in ('hasReplyEmoji', 'hasReplyBackgroundEmoji', 'hasReplyPatternEmoji') and p_count == 0:
                            m.setAccessible(True)
                            un = self.hook_method(m, MsgObjHasReplyEmojiHook())
                            if un:
                                self._xposed_unhooks.append(un)
                        elif m_name == 'getPeerColor' and p_count == 0:
                            m.setAccessible(True)
                            un = self.hook_method(m, MsgObjGetPeerColorHook())
                            if un:
                                self._xposed_unhooks.append(un)
                        elif m_name == 'getReplyPeerColor' and p_count == 0:
                            m.setAccessible(True)
                            un = self.hook_method(m, MsgObjGetReplyPeerColorHook())
                            if un:
                                self._xposed_unhooks.append(un)
                        elif m_name == 'getReplyColor' and p_count == 0:
                            m.setAccessible(True)
                            un = self.hook_method(m, MsgObjGetReplyColorHook())
                            if un:
                                self._xposed_unhooks.append(un)
                    except Exception as e:
                        log(f'SyncProfile: hook MessageObject method {m} error: {e}')
            if MessagesControllerClass:

                class GetUserHook(MethodHook):

                    def after_hooked_method(self, param):
                        try:
                            user_obj = param.getResult()
                            if user_obj:
                                plugin_self._patch_user_tl_object(user_obj)
                        except Exception:
                            pass

                class GetUserFullHook(MethodHook):

                    def after_hooked_method(self, param):
                        try:
                            fu_obj = param.getResult()
                            if fu_obj:
                                uid = getattr(fu_obj, 'id', 0)
                                if uid:
                                    plugin_self._patch_full_user_tl_object(fu_obj, int(uid))
                        except Exception:
                            pass

                class MessagesControllerIsPremiumHook(MethodHook):

                    def after_hooked_method(self, param):
                        try:
                            if plugin_self.get_setting('enable_local_premium', True):
                                param.setResult(True)
                        except Exception:
                            pass

                mc_methods = MessagesControllerClass.getDeclaredMethods()
                for m in mc_methods:
                    try:
                        m_name = m.getName()
                        if m_name == 'getUser':
                            m.setAccessible(True)
                            unhook = self.hook_method(m, GetUserHook())
                            if unhook:
                                self._xposed_unhooks.append(unhook)
                        elif m_name == 'getUserFull':
                            m.setAccessible(True)
                            unhook = self.hook_method(m, GetUserFullHook())
                            if unhook:
                                self._xposed_unhooks.append(unhook)
                        elif m_name in ('isUserPremium', 'isPremiumUser', 'hasPremium'):
                            m.setAccessible(True)
                            unhook = self.hook_method(m, MessagesControllerIsPremiumHook())
                            if unhook:
                                self._xposed_unhooks.append(unhook)

                    except Exception as e:
                        log(f'SyncProfile: hook MessagesController method {m} error: {e}')
            if MessagesStorageClass:
                ms_methods = MessagesStorageClass.getDeclaredMethods()
                for m in ms_methods:
                    try:
                        m_name = m.getName()
                        if m_name == 'getUser':
                            m.setAccessible(True)
                            unhook = self.hook_method(m, GetUserHook())
                            if unhook:
                                self._xposed_unhooks.append(unhook)
                    except Exception as e:
                        log(f'SyncProfile: hook MessagesStorage method {m} error: {e}')
            log(f'SyncProfile: Установлено {len(self._xposed_unhooks)} Java хуков.')
        except Exception as e:
            log(f'SyncProfile: Ошибка регистрации Java хуков: {e}')

    def _unregister_xposed_hooks(self):
        for unhook in self._xposed_unhooks:
            try:
                self.unhook_method(unhook)
            except Exception:
                pass
        self._xposed_unhooks.clear()

    def _queue_fetch_users_bulk(self, uids: List[int]):
        if not uids:
            return
        should_flush_now = False
        with self._sync_lock:
            for uid in uids:
                if not uid or uid <= 0:
                    continue
                if uid in self._profiles_cache or uid in self._unknown_uids_seen or uid in self._pending_user_ids:
                    continue
                self._pending_user_ids.add(uid)
            if len(self._pending_user_ids) >= 15:
                should_flush_now = True
            elif self._pending_user_ids and self._batch_timer is None:
                self._batch_timer = threading.Timer(0.05, self._execute_batch_fetch)
                self._batch_timer.daemon = True
                self._batch_timer.start()
        if should_flush_now:
            if HAS_ZWYLIB:
                async_manager.run_task(self._async_execute_batch())
            else:
                threading.Thread(target=self._execute_batch_fetch, daemon=True).start()

    def _queue_fetch_user(self, uid: int):
        if not uid or uid <= 0:
            return
        self._queue_fetch_users_bulk([uid])

    async def _async_execute_batch(self):
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, self._execute_batch_fetch)

    def _execute_batch_fetch(self):
        with self._sync_lock:
            if self._batch_timer:
                try:
                    self._batch_timer.cancel()
                except Exception:
                    pass
                self._batch_timer = None
            ids = list(self._pending_user_ids)
            self._pending_user_ids.clear()
        if not ids:
            return
        server_url = self.get_setting('server_url', DEFAULT_SERVER_URL).rstrip('/')
        cookie_val = self.get_setting('custom_cookie', DEFAULT_SECRET_COOKIE).strip()
        try:
            url = f'{server_url}/api/profiles/batch'
            payload = json.dumps({'user_ids': ids}).encode('utf-8')
            headers = {'Content-Type': 'application/json', 'User-Agent': f'SyncProfile/{__version__}', 'Cookie': f'{COOKIE_NAME}={cookie_val}'}
            req = urllib.request.Request(url, data=payload, headers=headers, method='POST')
            with urllib.request.urlopen(req, timeout=5) as resp:
                if resp.status == 200:
                    resp_data = json.loads(resp.read().decode('utf-8'))
                    profiles = resp_data.get('profiles', {})
                    if profiles:
                        with self._sync_lock:
                            for uid_str, p_data in profiles.items():
                                try:
                                    u_id = int(uid_str)
                                    self._profiles_cache[u_id] = p_data
                                    self._cache_dirty = True
                                except ValueError:
                                    continue
                        self._save_local_profiles_cache()

                        def on_batch_loaded():
                            try:
                                from org.telegram.messenger import MessagesController, NotificationCenter
                                from org.telegram.ui import LaunchActivity
                                for acc in range(4):
                                    mc = MessagesController.getInstance(acc)
                                    n_c = NotificationCenter.getInstance(acc)
                                    if mc and n_c:
                                        for u_id in ids:
                                            u = mc.getUser(u_id)
                                            if u:
                                                self._patch_user_tl_object(u)
                                                mc.putUser(u, True)
                                                try:
                                                    n_c.postNotificationName(NotificationCenter.userInfoDidLoad, int(u_id), u)
                                                except Exception:
                                                    pass
                                            fu = mc.getUserFull(u_id)
                                            if fu:
                                                self._patch_full_user_tl_object(fu, u_id)
                                                mc.putUserFull(fu)
                                                try:
                                                    n_c.postNotificationName(NotificationCenter.userFullDidLoad, int(u_id), fu)
                                                except Exception:
                                                    pass
                                        try:
                                            update_mask = getattr(NotificationCenter, 'UPDATE_MASK_ALL', 2147483647)
                                            n_c.postNotificationName(NotificationCenter.updateInterfaces, update_mask)
                                        except Exception:
                                            n_c.postNotificationName(NotificationCenter.updateInterfaces, 511)
                                        for notif_name in ('replaceMessagesObjects', 'replaceMessagesText', 'didUpdateMessagesViews', 'reloadDialogPhotos', 'peerColorsDidLoad', 'themeAccentListUpdated', 'emojiLoaded'):
                                            try:
                                                n_id = getattr(NotificationCenter, notif_name, None)
                                                if n_id is not None:
                                                    n_c.postNotificationName(n_id)
                                            except Exception:
                                                pass
                                g_nc = getattr(NotificationCenter, 'getGlobalInstance', lambda: None)()
                                if g_nc:
                                    try:
                                        update_mask = getattr(NotificationCenter, 'UPDATE_MASK_ALL', 2147483647)
                                        g_nc.postNotificationName(NotificationCenter.updateInterfaces, update_mask)
                                    except Exception:
                                        pass
                                la = getattr(LaunchActivity, 'instance', None)
                                if la:
                                    for layout_getter in ('getActionBarLayout', 'getRightActionBarLayout', 'getLayersActionBarLayout'):
                                        try:
                                            abl = getattr(la, layout_getter, lambda: None)()
                                            if abl:
                                                try:
                                                    pass
                                                except Exception:
                                                    pass
                                                try:
                                                    abl.invalidate()
                                                    abl.requestLayout()
                                                except Exception:
                                                    pass
                                        except Exception:
                                            pass
                            except Exception:
                                pass
                        run_on_ui_thread(on_batch_loaded)
                    else:
                        with self._sync_lock:
                            for u_id in ids:
                                self._unknown_uids_seen.add(u_id)
        except Exception as e:
            logger.warning(f'_execute_batch_fetch error: {e}')

    def _initial_background_sync(self):
        time.sleep(3)
        if not self._is_running:
            return
        self.sync_full_database_from_server(show_bulletin=False)

    async def _async_initial_background_sync(self):
        await asyncio.sleep(3)
        if not self._is_running:
            return
        await self._async_sync_database(show_bulletin=False)

    def _keep_alive_sync_loop(self):
        ticks = 0
        while self._is_running:
            time.sleep(20)
            if not self._is_running:
                break
            ticks += 1
            if self.get_setting('enable_sync', True):
                self._ensure_ayugram_premium()
                self._apply_all_to_all_accounts()
                if ticks >= 6:
                    ticks = 0
                    self.sync_delta_updates_from_server(show_bulletin=False)

    async def _async_keep_alive_sync_loop(self):
        ticks = 0
        while self._is_running:
            await asyncio.sleep(20)
            if not self._is_running:
                break
            ticks += 1
            if self.get_setting('enable_sync', True):
                self._ensure_ayugram_premium()
                self._apply_all_to_all_accounts()
                if ticks >= 6:
                    ticks = 0
                    await self._async_sync_delta_updates(show_bulletin=False)

    async def _async_sync_database(self, show_bulletin: bool=False, force_clean: bool=True):
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, lambda: self.sync_full_database_from_server(show_bulletin=show_bulletin, force_clean=force_clean))

    async def _async_sync_delta_updates(self, show_bulletin: bool=False):
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, lambda: self.sync_delta_updates_from_server(show_bulletin=show_bulletin))

    async def _async_push_account(self, acc_idx: int):
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, lambda: self.push_specific_account(acc_idx, show_ui_bulletin=False))

    def sync_delta_updates_from_server(self, show_bulletin: bool=False) -> bool:
        server_url = self.get_setting('server_url', DEFAULT_SERVER_URL).rstrip('/')
        auth_key = self.get_setting('auth_key', '').strip()
        cookie_val = self.get_setting('custom_cookie', DEFAULT_SECRET_COOKIE).strip()
        since_ts = int(self.get_setting('last_sync_timestamp', 0) or 0)
        try:
            url = f'{server_url}/api/profiles/updates?since={since_ts}'
            headers = {'User-Agent': f'SyncProfile/{__version__}', 'Cookie': f'{COOKIE_NAME}={cookie_val}'}
            if auth_key:
                headers['X-Auth-Key'] = auth_key
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=7) as resp:
                if resp.status == 200:
                    resp_data = json.loads(resp.read().decode('utf-8'))
                    profiles = resp_data.get('profiles', {})
                    new_cache: Dict[int, Dict[str, Any]] = {}
                    for uid_str, p_data in profiles.items():
                        try:
                            uid = int(uid_str)
                            new_cache[uid] = p_data
                        except ValueError:
                            continue
                    sync_time = int(resp_data.get('sync_time', time.time()) or time.time())
                    self.set_setting('last_sync_timestamp', sync_time, reload_settings=False)
                    if new_cache:
                        with self._sync_lock:
                            self._unknown_uids_seen.clear()
                            self._profiles_cache.update(new_cache)
                            self._cache_dirty = True
                        self._save_local_profiles_cache(force=True)
                        self._apply_all_to_all_accounts()
                        logger.info(f'Дельта-синхронизация: обновлено {len(new_cache)} профилей.')
                    if show_bulletin:
                        bulletins.show_success(f'Дельта-синхронизация: {len(new_cache)} обновлений.')
                    return True
                elif resp.status == 304:
                    if show_bulletin:
                        bulletins.show_info('База профилей уже актуальна (304).')
                    return True
        except urllib.error.HTTPError as e:
            if e.code == 304:
                if show_bulletin:
                    bulletins.show_info('База профилей уже актуальна.')
                return True
            logger.warning(f'Дельта-синхронизация HTTPError: {e}')
            if show_bulletin:
                bulletins.show_error(f'Сервер ответил со статусом: {e.code}')
        except Exception as e:
            logger.warning(f'Дельта-синхронизация error: {e}')
            if show_bulletin:
                bulletins.show_error(f'Ошибка дельта-синхронизации: {e}')
        return False

    def sync_full_database_from_server(self, show_bulletin: bool=False, force_clean: bool=True):
        server_url = self.get_setting('server_url', DEFAULT_SERVER_URL).rstrip('/')
        auth_key = self.get_setting('auth_key', '').strip()
        cookie_val = self.get_setting('custom_cookie', DEFAULT_SECRET_COOKIE).strip()
        try:
            url = f'{server_url}/api/profiles/all'
            headers = {'User-Agent': f'SyncProfile/{__version__}', 'Cookie': f'{COOKIE_NAME}={cookie_val}'}
            if auth_key:
                headers['X-Auth-Key'] = auth_key
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=7) as resp:
                if resp.status == 200:
                    resp_data = json.loads(resp.read().decode('utf-8'))
                    profiles = resp_data.get('profiles', {})
                    new_cache: Dict[int, Dict[str, Any]] = {}
                    for uid_str, p_data in profiles.items():
                        try:
                            uid = int(uid_str)
                            new_cache[uid] = p_data
                        except ValueError:
                            continue
                    with self._sync_lock:
                        self._unknown_uids_seen.clear()
                        self._profiles_cache.update(new_cache)
                        self._cache_dirty = True
                    self.set_setting('last_sync_timestamp', int(time.time()), reload_settings=False)
                    self._save_local_profiles_cache(force=True)
                    logger.info(f'База полностью обновлена. Скачано {len(new_cache)} актуальных профилей.')
                    self._apply_all_to_all_accounts()
                    if show_bulletin:
                        bulletins.show_success(f'База обновлена! Скачано {len(new_cache)} профилей.')
                elif show_bulletin:
                    bulletins.show_error(f'Сервер ответил со статусом: {resp.status}')
        except Exception as e:
            logger.error(f'Ошибка загрузки базы: {e}')
            if show_bulletin:
                bulletins.show_error(f'Ошибка загрузки базы: {e}')

    def _patch_user_tl_object(self, u: Any) -> bool:
        if not u:
            return False
        try:
            uid = int(getattr(u, 'id', 0) or 0)
        except Exception:
            return False
        if uid == 0:
            return False
        profile = None
        with self._sync_lock:
            profile = self._profiles_cache.get(uid)
        if not profile:
            self._queue_fetch_user(uid)
            return True
        try:
            from org.telegram.tgnet import TLRPC
            nc = int(profile.get('name_color', 0) or 0)
            if nc < 0:
                nc = 0
            nbg_val = profile.get('name_bg_emoji_id', '')
            nbg = 0
            if nbg_val is not None:
                try:
                    nbg_str = str(nbg_val).strip()
                    if nbg_str and nbg_str.isdigit():
                        nbg = int(nbg_str)
                except Exception:
                    nbg = 0
            prc = int(profile.get('profile_color', 0) or 0)
            if prc < 0:
                prc = 0
            pbg_val = profile.get('profile_bg_emoji_id', '')
            pbg = 0
            if pbg_val is not None:
                try:
                    pbg_str = str(pbg_val).strip()
                    if pbg_str and pbg_str.isdigit():
                        pbg = int(pbg_str)
                except Exception:
                    pbg = 0
            em_id_val = profile.get('emoji_status_id', '')
            em_id = 0
            if em_id_val is not None:
                try:
                    em_str = str(em_id_val).strip()
                    if em_str and em_str.isdigit():
                        em_id = int(em_str)
                except Exception:
                    em_id = 0
            if profile.get('premium', True):
                u.premium = True
                u.flags = int(getattr(u, 'flags', 0) | 268435456)
            u.color = _build_peer_color(nc, nbg)
            u.profile_color = _build_peer_color(prc, pbg)
            f2 = int(getattr(u, 'flags2', 0) | 256 | 512)
            if profile.get('premium', True):
                f2 |= 2
            if em_id != 0:
                st = TLRPC.TL_emojiStatus()
                st.document_id = int(em_id)
                u.emoji_status = st
                f2 |= 4096 | 1
            u.flags2 = f2
            return True
        except Exception:
            return False

    def _patch_full_user_tl_object(self, fu: Any, uid: int=0) -> bool:
        if not fu:
            return False
        try:
            if uid == 0:
                uid = self._extract_peer_uid(fu)
        except Exception:
            return False
        if uid == 0:
            return False
        profile = None
        with self._sync_lock:
            profile = self._profiles_cache.get(uid)
        if not profile:
            self._queue_fetch_user(uid)
            return True
        try:
            nc = int(profile.get('name_color', 0) or 0)
            if nc < 0:
                nc = 0
            nbg_val = profile.get('name_bg_emoji_id', '')
            nbg = 0
            if nbg_val is not None:
                try:
                    nbg_str = str(nbg_val).strip()
                    if nbg_str and nbg_str.isdigit():
                        nbg = int(nbg_str)
                except Exception:
                    nbg = 0
            prc = int(profile.get('profile_color', 0) or 0)
            if prc < 0:
                prc = 0
            pbg_val = profile.get('profile_bg_emoji_id', '')
            pbg = 0
            if pbg_val is not None:
                try:
                    pbg_str = str(pbg_val).strip()
                    if pbg_str and pbg_str.isdigit():
                        pbg = int(pbg_str)
                except Exception:
                    pbg = 0
            fu.profile_color = _build_peer_color(prc, pbg)
            f2 = int(getattr(fu, 'flags2', 0) | 512)
            if hasattr(fu, 'color'):
                fu.color = _build_peer_color(nc, nbg)
                f2 |= 256
            fu.flags2 = f2
            if hasattr(fu, 'flags'):
                fu.flags = int(getattr(fu, 'flags', 0) | 512)
            if hasattr(fu, 'user') and fu.user:
                self._patch_user_tl_object(fu.user)
            return True
        except Exception:
            return False

    def _apply_all_to_all_accounts(self):

        def ui_update_task():
            try:
                from java.util import ArrayList
                from org.telegram.messenger import MessagesController, MessagesStorage, NotificationCenter, UserConfig
                from org.telegram.tgnet import TLRPC
                active_accs = self._get_active_accounts_data()
                for acc_info in active_accs:
                    acc_idx = acc_info.get('acc_idx', 0)
                    my_uid = acc_info.get('user_id', 0)
                    if my_uid != 0:
                        my_p = self._get_profile_dict_for_slot(acc_idx, my_uid)
                        with self._sync_lock:
                            self._profiles_cache[my_uid] = my_p
                            self._cache_dirty = True
                self._ensure_ayugram_premium()
                with self._sync_lock:
                    items = list(self._profiles_cache.items())
                for acc in range(4):
                    try:
                        u_cfg = UserConfig.getInstance(acc)
                        if not u_cfg or not u_cfg.isClientActivated():
                            continue
                        try:
                            u_cfg.loadConfig()
                        except Exception:
                            pass
                        mc = MessagesController.getInstance(acc)
                        ms = MessagesStorage.getInstance(acc)
                        if not mc:
                            continue
                        users_to_save = ArrayList()
                        for uid, p in items:
                            u = mc.getUser(uid)
                            if not u and ms:
                                try:
                                    u = ms.getUser(uid)
                                except Exception:
                                    u = None
                            if not u:
                                try:
                                    u = TLRPC.TL_user()
                                    u.id = int(uid)
                                    u.flags = 0
                                    u.flags2 = 0
                                except Exception:
                                    u = None
                            if u:
                                self._patch_user_tl_object(u)
                                mc.putUser(u, True)
                                users_to_save.add(u)
                            fu = mc.getUserFull(uid)
                            if fu:
                                self._patch_full_user_tl_object(fu, uid)
                                mc.putUserFull(fu)
                        curr_u = u_cfg.getCurrentUser()
                        my_acc_uid = int(u_cfg.getClientUserId() or (getattr(curr_u, 'id', 0) if curr_u else 0))
                        if curr_u and my_acc_uid != 0:
                            slot_p = self._get_profile_dict_for_slot(acc, my_acc_uid)
                            if slot_p.get('premium', True):
                                curr_u.premium = True
                                curr_u.flags = int(getattr(curr_u, 'flags', 0) | 268435456)
                            curr_u.color = _build_peer_color(int(slot_p['name_color']), int(slot_p['name_bg_emoji_id']))
                            curr_u.profile_color = _build_peer_color(int(slot_p['profile_color']), int(slot_p['profile_bg_emoji_id']))
                            f2 = int(getattr(curr_u, 'flags2', 0) | 256 | 512)
                            if slot_p.get('premium', True):
                                f2 |= 2
                            em_id = int(slot_p.get('emoji_status_id', 0) or 0)
                            if em_id != 0:
                                st = TLRPC.TL_emojiStatus()
                                st.document_id = em_id
                                curr_u.emoji_status = st
                                f2 |= 4096 | 1
                            curr_u.flags2 = f2
                            mc.putUser(curr_u, True)
                            users_to_save.add(curr_u)
                            try:
                                u_cfg.saveConfig(False)
                            except Exception:
                                pass
                        if ms and users_to_save.size() > 0:
                            try:
                                ms.putUsersAndChats(users_to_save, None, True, True)
                            except Exception:
                                pass
                        n_c = NotificationCenter.getInstance(acc)
                        if n_c:
                            for uid, p in items:
                                u_item = mc.getUser(uid)
                                if u_item:
                                    try:
                                        n_c.postNotificationName(NotificationCenter.userInfoDidLoad, int(uid), u_item)
                                    except Exception:
                                        pass
                                fu_item = mc.getUserFull(uid)
                                if fu_item:
                                    try:
                                        n_c.postNotificationName(NotificationCenter.userFullDidLoad, int(uid), fu_item)
                                    except Exception:
                                        pass
                            if curr_u and my_acc_uid != 0:
                                try:
                                    n_c.postNotificationName(NotificationCenter.userInfoDidLoad, int(my_acc_uid), curr_u)
                                except Exception:
                                    pass
                                fu_my = mc.getUserFull(my_acc_uid)
                                if fu_my:
                                    try:
                                        n_c.postNotificationName(NotificationCenter.userFullDidLoad, int(my_acc_uid), fu_my)
                                    except Exception:
                                        pass
                            try:
                                update_mask = getattr(NotificationCenter, 'UPDATE_MASK_ALL', 2147483647)
                                n_c.postNotificationName(NotificationCenter.updateInterfaces, update_mask)
                            except Exception:
                                n_c.postNotificationName(NotificationCenter.updateInterfaces, 511)
                            for notif_name in ('mainUserInfoChanged', 'currentUserPremiumStatusChanged', 'reloadDialogPhotos', 'didUpdateMessagesViews', 'replaceMessagesObjects', 'replaceMessagesText', 'peerColorsDidLoad', 'themeAccentListUpdated'):
                                try:
                                    n_id = getattr(NotificationCenter, notif_name, None)
                                    if n_id is not None:
                                        n_c.postNotificationName(n_id)
                                except Exception:
                                    pass
                        if acc == UserConfig.selectedAccount:
                            try:
                                from com.radolyn.ayugram import AyuConfig
                                sel_p = self._get_profile_dict_for_slot(acc, my_acc_uid)
                                AyuConfig.nameColor = int(sel_p['name_color'])
                                AyuConfig.nameCustomEmojiId = int(sel_p['name_bg_emoji_id'])
                                AyuConfig.profileColor = int(sel_p['profile_color'])
                                AyuConfig.profileCustomEmojiId = int(sel_p['profile_bg_emoji_id'])
                                AyuConfig.statusEmojiId = int(sel_p['emoji_status_id'])
                                if hasattr(AyuConfig, 'localPremium') and self.get_setting('enable_local_premium', True):
                                    AyuConfig.localPremium = True
                                if hasattr(AyuConfig, 'saveConfig'):
                                    AyuConfig.saveConfig()
                                elif hasattr(AyuConfig, 'save'):
                                    AyuConfig.save()
                            except Exception:
                                pass
                    except Exception as e:
                        log(f'SyncProfile: _apply_all_to_all_accounts acc {acc} error: {e}')
                try:
                    g_nc = getattr(NotificationCenter, 'getGlobalInstance', lambda: None)()
                    if g_nc:
                        try:
                            update_mask = getattr(NotificationCenter, 'UPDATE_MASK_ALL', 2147483647)
                            g_nc.postNotificationName(NotificationCenter.updateInterfaces, update_mask)
                        except Exception:
                            pass
                        for notif_name in ('mainUserInfoChanged', 'currentUserPremiumStatusChanged', 'reloadDialogPhotos', 'themeAccentListUpdated', 'emojiLoaded'):
                            try:
                                n_id = getattr(NotificationCenter, notif_name, None)
                                if n_id is not None:
                                    g_nc.postNotificationName(n_id)
                            except Exception:
                                pass
                except Exception:
                    pass
                try:
                    from org.telegram.ui import LaunchActivity
                    la = getattr(LaunchActivity, 'instance', None)
                    if la:
                        for layout_getter in ('getActionBarLayout', 'getRightActionBarLayout', 'getLayersActionBarLayout'):
                            try:
                                abl = getattr(la, layout_getter, lambda: None)()
                                if abl:
                                    try:
                                        pass
                                    except Exception:
                                        pass
                                    try:
                                        abl.invalidate()
                                        abl.requestLayout()
                                    except Exception:
                                        pass
                            except Exception:
                                pass
                except Exception:
                    pass
            except Exception as e:
                log(f'SyncProfile: _apply_all_to_all_accounts error: {e}')
        run_on_ui_thread(ui_update_task)

    def _extract_peer_uid(self, peer: Any) -> int:
        if not peer:
            return 0
        try:
            if isinstance(peer, (int, float)):
                val = int(peer)
                return val if val > 0 else 0
            for attr in ('user_id', 'id', 'channel_id', 'chat_id'):
                uid = getattr(peer, attr, 0)
                if uid:
                    val = int(uid)
                    if val > 0:
                        return val
        except Exception:
            pass
        return 0

    def _patch_response_entities(self, obj: Any):
        if not obj or not self.get_setting('enable_sync', True):
            return
        try:
            missing_uids: List[int] = []
            users = getattr(obj, 'users', None)
            if users:
                u_count = users.size() if hasattr(users, 'size') else len(users)
                for i in range(u_count):
                    try:
                        u = users.get(i) if hasattr(users, 'get') else users[i]
                        if u:
                            if not self._patch_user_tl_object(u):
                                u_id = int(getattr(u, 'id', 0) or 0)
                                if u_id > 0:
                                    missing_uids.append(u_id)
                    except Exception:
                        pass
            user = getattr(obj, 'user', None)
            if user:
                try:
                    if not self._patch_user_tl_object(user):
                        u_id = int(getattr(user, 'id', 0) or 0)
                        if u_id > 0:
                            missing_uids.append(u_id)
                except Exception:
                    pass
            full_user = getattr(obj, 'full_user', None)
            if full_user:
                try:
                    target_uid = 0
                    if users:
                        first_u = users.get(0) if hasattr(users, 'get') else users[0]
                        if first_u:
                            target_uid = int(getattr(first_u, 'id', 0) or 0)
                    if target_uid == 0 and user:
                        target_uid = int(getattr(user, 'id', 0) or 0)
                    if target_uid == 0:
                        target_uid = int(getattr(full_user, 'id', 0) or 0)
                    if target_uid != 0:
                        if not self._patch_full_user_tl_object(full_user, target_uid):
                            missing_uids.append(target_uid)
                except Exception:
                    pass
            messages = getattr(obj, 'messages', None)
            if messages:
                m_count = messages.size() if hasattr(messages, 'size') else len(messages)
                for i in range(min(m_count, 100)):
                    try:
                        m = messages.get(i) if hasattr(messages, 'get') else messages[i]
                        if not m:
                            continue
                        fid = self._extract_peer_uid(getattr(m, 'from_id', None))
                        if fid > 0 and fid not in self._profiles_cache:
                            missing_uids.append(fid)
                        r_hdr = getattr(m, 'reply_to', None)
                        if r_hdr:
                            r_peer = getattr(r_hdr, 'reply_to_peer_id', None)
                            r_uid = self._extract_peer_uid(r_peer)
                            if r_uid > 0 and r_uid not in self._profiles_cache:
                                missing_uids.append(r_uid)
                            r_from = getattr(r_hdr, 'reply_from', None)
                            if r_from:
                                rf_peer = getattr(r_from, 'from_id', None)
                                rf_uid = self._extract_peer_uid(rf_peer)
                                if rf_uid > 0 and rf_uid not in self._profiles_cache:
                                    missing_uids.append(rf_uid)
                        fwd = getattr(m, 'fwd_from', None)
                        if fwd:
                            fwd_peer = getattr(fwd, 'from_id', None)
                            fwd_uid = self._extract_peer_uid(fwd_peer)
                            if fwd_uid > 0 and fwd_uid not in self._profiles_cache:
                                missing_uids.append(fwd_uid)
                    except Exception:
                        pass
            updates = getattr(obj, 'updates', None)
            if updates:
                upd_count = updates.size() if hasattr(updates, 'size') else len(updates)
                for i in range(upd_count):
                    try:
                        upd = updates.get(i) if hasattr(updates, 'get') else updates[i]
                        if not upd:
                            continue
                        nested_users = getattr(upd, 'users', None)
                        if nested_users:
                            nu_count = nested_users.size() if hasattr(nested_users, 'size') else len(nested_users)
                            for j in range(nu_count):
                                try:
                                    nu = nested_users.get(j) if hasattr(nested_users, 'get') else nested_users[j]
                                    if nu:
                                        if not self._patch_user_tl_object(nu):
                                            nu_id = int(getattr(nu, 'id', 0) or 0)
                                            if nu_id > 0:
                                                missing_uids.append(nu_id)
                                except Exception:
                                    pass
                        n_msg = getattr(upd, 'message', None)
                        if n_msg:
                            fid = self._extract_peer_uid(getattr(n_msg, 'from_id', None))
                            if fid > 0 and fid not in self._profiles_cache:
                                missing_uids.append(fid)
                    except Exception:
                        pass
            if missing_uids:
                self._queue_fetch_users_bulk(missing_uids)
        except Exception as e:
            log(f'SyncProfile: _patch_response_entities error: {e}')

    def post_request_hook(self, request_name: str, account: int, response: Any, error: Any) -> HookResult:
        if error or not response or (not self.get_setting('enable_sync', True)):
            return HookResult()
        self._patch_response_entities(response)
        return HookResult()

    def on_updates_hook(self, container_name: str, account: int, updates: Any) -> HookResult:
        if not updates or not self.get_setting('enable_sync', True):
            return HookResult()
        self._patch_response_entities(updates)
        return HookResult()

    def grab_settings_from_fake_premium(self, target_acc_idx: int=-1, show_bulletin: bool=True):
        try:
            from org.telegram.messenger import UserConfig
            if target_acc_idx == -1:
                target_acc_idx = getattr(UserConfig, 'selectedAccount', 0)
        except Exception:
            target_acc_idx = 0
        found_any = False
        name = f'Аккаунт {target_acc_idx + 1}'
        extracted_data: Dict[str, Any] = {}
        try:
            AyuConfigClass = find_class('com.radolyn.ayugram.AyuConfig')
            if AyuConfigClass:
                for f in AyuConfigClass.getDeclaredFields():
                    try:
                        f.setAccessible(True)
                        fname = f.getName().lower()
                        fval = f.get(None)
                        if fval is not None:
                            if 'profile' in fname and 'color' in fname and ('emoji' not in fname):
                                pc = int(fval)
                                if pc >= 0:
                                    extracted_data['profile_color'] = pc
                            elif 'name' in fname and 'color' in fname and ('emoji' not in fname):
                                nc = int(fval)
                                if nc >= 0:
                                    extracted_data['name_color'] = nc
                            elif 'profile' in fname and 'emoji' in fname:
                                pem = str(fval).strip()
                                if pem and pem not in ('0', '-1', 'None'):
                                    extracted_data['profile_bg_emoji_id'] = pem
                            elif 'name' in fname and 'emoji' in fname:
                                nem = str(fval).strip()
                                if nem and nem not in ('0', '-1', 'None'):
                                    extracted_data['name_bg_emoji_id'] = nem
                            elif 'status' in fname and 'emoji' in fname:
                                sem = str(fval).strip()
                                if sem and sem not in ('0', '-1', 'None'):
                                    extracted_data['emoji_status_id'] = sem
                    except Exception:
                        pass
        except Exception:
            pass
        try:
            from org.telegram.messenger import ApplicationLoader
            ctx = getattr(ApplicationLoader, 'applicationContext', None)
            if ctx and hasattr(ctx, 'getSharedPreferences'):
                for pref_file in ('ayuprefs', 'ayuconfig', 'ayu', 'ayugram', 'mainconfig', 'userconfing', 'extera'):
                    try:
                        sp = ctx.getSharedPreferences(pref_file, 0)
                        if sp:
                            all_entries = sp.getAll()
                            if all_entries:
                                for entry in all_entries.entrySet():
                                    k_name = str(entry.getKey()).lower()
                                    raw_val = entry.getValue()
                                    val_str = str(raw_val).strip() if raw_val is not None else ''
                                    if not val_str or val_str in ('0', '-1', 'None'):
                                        continue
                                    if 'name' in k_name and 'color' in k_name and ('emoji' not in k_name):
                                        try:
                                            extracted_data['name_color'] = int(val_str)
                                        except Exception:
                                            pass
                                    elif 'profile' in k_name and 'color' in k_name and ('emoji' not in k_name):
                                        try:
                                            extracted_data['profile_color'] = int(val_str)
                                        except Exception:
                                            pass
                                    elif 'name' in k_name and ('emoji' in k_name or 'pattern' in k_name):
                                        extracted_data['name_bg_emoji_id'] = val_str
                                    elif 'profile' in k_name and ('emoji' in k_name or 'pattern' in k_name):
                                        extracted_data['profile_bg_emoji_id'] = val_str
                                    elif 'status' in k_name and 'emoji' in k_name:
                                        extracted_data['emoji_status_id'] = val_str
                    except Exception:
                        pass
        except Exception:
            pass
        try:
            from org.telegram.messenger import UserConfig, MessagesController
            u_cfg = UserConfig.getInstance(target_acc_idx)
            mc = MessagesController.getInstance(target_acc_idx) if hasattr(MessagesController, 'getInstance') else None
            users_list = []
            if u_cfg:
                try:
                    u_cfg.loadConfig()
                except Exception:
                    pass
                cu = u_cfg.getCurrentUser()
                if cu:
                    users_list.append(cu)
                    name = str(getattr(cu, 'first_name', '') or name)
                my_id = int(u_cfg.getClientUserId() or 0)
                if mc and my_id > 0:
                    mcu = mc.getUser(my_id)
                    if mcu and mcu not in users_list:
                        users_list.append(mcu)
                    uf = mc.getUserFull(my_id)
                    if uf and hasattr(uf, 'profile_color') and (uf.profile_color is not None):
                        pc_val = getattr(uf.profile_color, 'color', None)
                        if pc_val is not None:
                            extracted_data['profile_color'] = int(pc_val)
                        pc_em = getattr(uf.profile_color, 'background_emoji_id', None)
                        if pc_em:
                            extracted_data['profile_bg_emoji_id'] = str(pc_em)
            for u in users_list:
                if hasattr(u, 'color') and u.color is not None:
                    c_obj = u.color
                    if isinstance(c_obj, int):
                        extracted_data['name_color'] = c_obj
                    else:
                        c_val = getattr(c_obj, 'color', None)
                        if c_val is not None:
                            extracted_data['name_color'] = int(c_val)
                        c_em = getattr(c_obj, 'background_emoji_id', None)
                        if c_em:
                            extracted_data['name_bg_emoji_id'] = str(c_em)
                if hasattr(u, 'profile_color') and u.profile_color is not None:
                    pc_obj = u.profile_color
                    if isinstance(pc_obj, int):
                        extracted_data['profile_color'] = pc_obj
                    else:
                        pc_val = getattr(pc_obj, 'color', None)
                        if pc_val is not None:
                            extracted_data['profile_color'] = int(pc_val)
                        pc_em = getattr(pc_obj, 'background_emoji_id', None)
                        if pc_em:
                            extracted_data['profile_bg_emoji_id'] = str(pc_em)
                if hasattr(u, 'emoji_status') and u.emoji_status is not None:
                    em_obj = u.emoji_status
                    if isinstance(em_obj, (int, str)):
                        extracted_data['emoji_status_id'] = str(em_obj)
                    else:
                        doc_id = getattr(em_obj, 'document_id', None)
                        if doc_id:
                            extracted_data['emoji_status_id'] = str(doc_id)
        except Exception as e:
            log(f'SyncProfile: Error extracting user configs: {e}')
        for k, v in extracted_data.items():
            self._set_slot_val(target_acc_idx, k, v)
            found_any = True
        self._set_slot_val(target_acc_idx, 'premium', True)
        self.set_setting(f'slot_{target_acc_idx}_configured', True, reload_settings=True)
        self._save_local_profiles_cache(force=True)
        self._apply_all_to_all_accounts()
        if show_bulletin:
            if found_any:
                cur_nc = self._get_slot_val(target_acc_idx, 'name_color', 0)
                cur_pc = self._get_slot_val(target_acc_idx, 'profile_color', 0)
                run_on_ui_thread(lambda: BulletinHelper.show_success(f"✨ Настройки Fake Premium загружены для {name}!\nИмя/Реплаи: #{cur_nc} | Обложка: #{cur_pc}\nНажмите '🚀 Опубликовать', чтобы отправить на сервер!"))
            else:
                run_on_ui_thread(lambda: BulletinHelper.show_info(f"В Telegram сначала нажмите 'Применить стиль' в меню цветов, а затем повторите считывание."))

    def grab_settings_from_ayugram(self, target_acc_idx: int=-1):
        self.grab_settings_from_fake_premium(target_acc_idx=target_acc_idx, show_bulletin=True)

    def push_specific_account(self, acc_idx: int, show_ui_bulletin: bool=True):
        uid = 0
        name = f'Аккаунт {acc_idx + 1}'
        try:
            from org.telegram.messenger import UserConfig
            u_c = UserConfig.getInstance(acc_idx)
            if u_c:
                try:
                    u_c.loadConfig()
                except Exception:
                    pass
                uid = int(u_c.getClientUserId() or 0)
                curr_user = u_c.getCurrentUser()
                if curr_user:
                    name = str(getattr(curr_user, 'first_name', '') or name)
        except Exception:
            pass
        if uid == 0:
            uid = int(self.get_setting('custom_my_user_id', 0) or 0)
        if uid == 0:
            if show_ui_bulletin:
                bulletins.show_error(f'Не удалось определить Telegram ID для аккаунта {acc_idx + 1}.')
            return
        profile_data = self._get_profile_dict_for_slot(acc_idx, uid)

        def worker():
            server_url = self.get_setting('server_url', DEFAULT_SERVER_URL).rstrip('/')
            cookie_val = self.get_setting('custom_cookie', DEFAULT_SECRET_COOKIE).strip()
            try:
                url = f'{server_url}/api/profile'
                payload = json.dumps(profile_data).encode('utf-8')
                headers = {'Content-Type': 'application/json', 'User-Agent': f'SyncProfile/{__version__}', 'Cookie': f'{COOKIE_NAME}={cookie_val}'}
                req = urllib.request.Request(url, data=payload, headers=headers, method='POST')
                with urllib.request.urlopen(req, timeout=6) as resp:
                    if resp.status == 200:
                        with self._sync_lock:
                            self._profiles_cache[uid] = profile_data
                            self._cache_dirty = True
                        self._save_local_profiles_cache()

                        def on_success():
                            self._apply_all_to_all_accounts()
                            if show_ui_bulletin:
                                bulletins.show_success(f"✅ {name} опубликован!\nID: {uid}\nЦвет: #{profile_data['name_color']} | Обложка: #{profile_data['profile_color']}\nУзор: {profile_data['name_bg_emoji_id']}\nЭмодзи: {profile_data['emoji_status_id']}")
                        run_on_ui_thread(on_success)
                    elif show_ui_bulletin:
                        bulletins.show_error(f'Сервер вернул статус: {resp.status}')
            except Exception as e:
                logger.error(f'Ошибка публикации аккаунта {acc_idx}: {e}')
                if show_ui_bulletin:
                    bulletins.show_error(f'Ошибка публикации: {e}')
        threading.Thread(target=worker, daemon=True).start()

    def push_all_accounts(self, show_ui_bulletin: bool=True):
        active_accs = self._get_active_accounts_data()
        server_url = self.get_setting('server_url', DEFAULT_SERVER_URL).rstrip('/')
        cookie_val = self.get_setting('custom_cookie', DEFAULT_SECRET_COOKIE).strip()

        def worker():
            success_count = 0
            for acc_info in active_accs:
                acc_idx = acc_info.get('acc_idx', 0)
                uid = acc_info.get('user_id', 0)
                if uid == 0:
                    continue
                profile_data = self._get_profile_dict_for_slot(acc_idx, uid)
                try:
                    url = f'{server_url}/api/profile'
                    payload = json.dumps(profile_data).encode('utf-8')
                    headers = {'Content-Type': 'application/json', 'User-Agent': f'SyncProfile/{__version__}', 'Cookie': f'{COOKIE_NAME}={cookie_val}'}
                    req = urllib.request.Request(url, data=payload, headers=headers, method='POST')
                    with urllib.request.urlopen(req, timeout=6) as resp:
                        if resp.status == 200:
                            with self._sync_lock:
                                self._profiles_cache[uid] = profile_data
                                self._cache_dirty = True
                            success_count += 1
                except Exception as e:
                    logger.error(f'Ошибка публикации всех (акк {acc_idx}): {e}')
            self._save_local_profiles_cache()

            def on_done():
                self._apply_all_to_all_accounts()
                if show_ui_bulletin:
                    if success_count > 0:
                        bulletins.show_success(f'✅ Успешно синхронизировано {success_count} аккаунтов!')
                    else:
                        bulletins.show_error('Не удалось синхронизировать аккаунты.')
            run_on_ui_thread(on_done)
        threading.Thread(target=worker, daemon=True).start()

    def _save_local_profiles_cache(self, force: bool=False):
        try:
            with self._sync_lock:
                if not force and (not self._cache_dirty):
                    return
                cache_copy = dict(self._profiles_cache)
                self._cache_dirty = False
            if HAS_ZWYLIB and self._json_cache_file is not None:
                self._json_cache_file.content = cache_copy
                self._json_cache_file.write()
                return
            try:
                import os
                cache_path = 'sync_profiles_cache.json'
                with open(cache_path, 'w', encoding='utf-8') as f:
                    json.dump(cache_copy, f, ensure_ascii=False)
                return
            except Exception:
                pass
            cache_str = json.dumps(cache_copy, ensure_ascii=False)
            self.set_setting('_local_profiles_json', cache_str, reload_settings=False)
        except Exception as e:
            logger.error(f'Save cache error: {e}')

    def _load_local_profiles_cache(self):
        try:
            if HAS_ZWYLIB and self._json_cache_file is not None:
                self._json_cache_file.read()
                cnt = self._json_cache_file.content
                if isinstance(cnt, dict) and cnt:
                    with self._sync_lock:
                        for uid_str, p_data in cnt.items():
                            if str(uid_str).isdigit():
                                self._profiles_cache[int(uid_str)] = p_data
                    return
            import os
            cache_path = 'sync_profiles_cache.json'
            if os.path.exists(cache_path):
                with open(cache_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    if isinstance(data, dict):
                        with self._sync_lock:
                            for uid_str, p_data in data.items():
                                if str(uid_str).isdigit():
                                    self._profiles_cache[int(uid_str)] = p_data
                        return
            saved_str = self.get_setting('_local_profiles_json', '{}')
            if saved_str and saved_str != '{}':
                saved_dict = json.loads(saved_str)
                with self._sync_lock:
                    for uid_str, p_data in saved_dict.items():
                        if str(uid_str).isdigit():
                            self._profiles_cache[int(uid_str)] = p_data
                self._save_local_profiles_cache(force=True)
                self.set_setting('_local_profiles_json', '{}', reload_settings=False)
        except Exception as e:
            logger.error(f'Load cache error: {e}')

    def _interactive_pick_reply_color(self, acc_idx: int):
        if not HAS_ZWYLIB:
            return

        async def _worker():
            cur_c = int(self._get_slot_val(acc_idx, 'name_color', 0) or 0)
            chosen = await UI.SelectorDialog.show('🎨 Выберите цвет имени и реплаев', NAME_AND_REPLY_COLORS, current_index=cur_c)
            if chosen is not None:
                self._set_slot_val(acc_idx, 'name_color', chosen)
                self._save_local_profiles_cache(force=True)
                self._apply_all_to_all_accounts()
                self.push_specific_account(acc_idx, show_ui_bulletin=False)
                bulletins.show_success(f'Цвет имени обновлен: {NAME_AND_REPLY_COLORS[chosen]}')
        async_manager.run_task(_worker())

    def _interactive_pick_profile_color(self, acc_idx: int):
        if not HAS_ZWYLIB:
            return

        async def _worker():
            cur_c = int(self._get_slot_val(acc_idx, 'profile_color', 0) or 0)
            chosen = await UI.SelectorDialog.show('🖼️ Выберите цвет фона профиля (обложки)', PROFILE_COLORS, current_index=cur_c)
            if chosen is not None:
                self._set_slot_val(acc_idx, 'profile_color', chosen)
                self._save_local_profiles_cache(force=True)
                self._apply_all_to_all_accounts()
                self.push_specific_account(acc_idx, show_ui_bulletin=False)
                bulletins.show_success(f'Цвет обложки обновлен: {PROFILE_COLORS[chosen]}')
        async_manager.run_task(_worker())

    def _interactive_input_emoji_id(self, acc_idx: int, field_key: str, title: str):
        if not HAS_ZWYLIB:
            return

        async def _worker():
            cur_val = str(self._get_slot_val(acc_idx, field_key, '') or '')
            res = await UI.StringInputDialog.show(title, initial_text=cur_val, hint='Document ID (например: 5299025466055734222)')
            if res is not None:
                clean_val = str(res).strip()
                self._set_slot_val(acc_idx, field_key, clean_val)
                self._save_local_profiles_cache(force=True)
                self._apply_all_to_all_accounts()
                self.push_specific_account(acc_idx, show_ui_bulletin=False)
                bulletins.show_success(f"✨ Сохранено: {clean_val or 'Очищено'}")
        async_manager.run_task(_worker())

    def _interactive_live_preview_dialog(self, acc_idx: int):
        active_accs = self._get_active_accounts_data()
        acc_info = next((a for a in active_accs if a.get('acc_idx') == acc_idx), None)
        uid = acc_info.get('user_id', 0) if acc_info else 0
        name = acc_info.get('name', f'Аккаунт {acc_idx + 1}') if acc_info else f'Аккаунт {acc_idx + 1}'
        cur_prem = bool(self._get_slot_val(acc_idx, 'premium', True))
        cur_name_c = int(self._get_slot_val(acc_idx, 'name_color', 0) or 0)
        cur_prof_c = int(self._get_slot_val(acc_idx, 'profile_color', 0) or 0)
        cur_em_id = str(self._get_slot_val(acc_idx, 'emoji_status_id', '') or '').strip()
        cur_name_bg = str(self._get_slot_val(acc_idx, 'name_bg_emoji_id', '') or '').strip()
        cur_prof_bg = str(self._get_slot_val(acc_idx, 'profile_bg_emoji_id', '') or '').strip()
        name_c_str = NAME_AND_REPLY_COLORS[cur_name_c] if 0 <= cur_name_c < len(NAME_AND_REPLY_COLORS) else f'ID {cur_name_c}'
        prof_c_str = PROFILE_COLORS[cur_prof_c] if 0 <= cur_prof_c < len(PROFILE_COLORS) else f'ID {cur_prof_c}'
        em_display = cur_em_id if cur_em_id else '—'
        name_bg_display = cur_name_bg if cur_name_bg else '—'
        prof_bg_display = cur_prof_bg if cur_prof_bg else '—'
        preview_msg = f"👤 Аккаунт: {name} (ID: {uid})\n\n⭐ TG Premium: {('Активен' if cur_prem else 'Выключен')}\n🎨 Цвет имени: {name_c_str}\n🖼️ Цвет обложки: {prof_c_str}\n⭐ Эмодзи-статус: {em_display}\n✨ Узор имени: {name_bg_display}\n✨ Узор обложки: {prof_bg_display}\n\n💬 Пример сообщения:\n┌ {name} {('⭐' if cur_prem else '')}\n│ Профиль синхронизирован через SyncProfile Node ✨\n└ 12:34 ✓✓"
        if HAS_ZWYLIB:
            dialog = UI.AlertDialog(title=f'👁️ Предпросмотр: {name}', text=preview_msg, buttons=[UI.AlertButton('Закрыть'), UI.AlertButton('🚀 Опубликовать', on_click=lambda b, w: self.push_specific_account(acc_idx, show_ui_bulletin=True))])
            dialog.show()
        else:
            bulletins.show_info(preview_msg)

    def _interactive_sync_bottom_sheet(self):
        if not HAS_ZWYLIB:
            threading.Thread(target=lambda: self.sync_full_database_from_server(show_bulletin=True, force_clean=True), daemon=True).start()
            return

        def _sheet_worker(sheet: Any):
            try:
                sheet.update_status(0.2, 'Подключение к серверу синхронизации...')
                time.sleep(0.2)
                sheet.update_status(0.5, 'Загрузка актуальной базы профилей...')
                self.sync_full_database_from_server(show_bulletin=False, force_clean=True)
                sheet.update_status(0.85, 'Применение настроек ко всем аккаунтам...')
                time.sleep(0.3)
                with self._sync_lock:
                    total = len(self._profiles_cache)
                sheet.update_status(1.0, f'Готово! Загружено профилей: {total}')
                time.sleep(0.5)
                sheet.finish()
            except Exception as e:
                sheet.update_status(1.0, f'Ошибка: {e}')
                time.sleep(1.0)
                sheet.finish()
        sheet = UI.BottomSheet(title='SyncProfile Cloud Sync', description='Запуск синхронизации...', sticker='exteraPlugins/1', worker=_sheet_worker, on_finish=lambda s: bulletins.show_success('База профилей успешно обновлена!'))
        sheet.show()
        sheet.start_worker()

    def _interactive_clear_cache_dialog(self, view: Any=None):
        if not HAS_ZWYLIB:
            self._clear_cache_action(view)
            return

        def _do_clear():
            with self._sync_lock:
                self._profiles_cache.clear()
                self._cache_dirty = False
            if self._json_cache_file:
                try:
                    self._json_cache_file.wipe()
                except Exception:
                    pass
            self._save_local_profiles_cache(force=True)
            self._apply_all_to_all_accounts()
            bulletins.show_success('Локальный кэш полностью очищен.')
        dialog = UI.AlertDialog(title='Очистить локальный кэш?', text='Все скачанные профили других пользователей будут удалены из локального кэша. Ваши собственные настройки останутся нетронутыми.', buttons=[UI.AlertButton('Отмена'), UI.AlertButton('Очистить', red=True, on_click=lambda b, w: _do_clear())])
        dialog.show()

    def _register_menu_items(self):
        self.add_menu_item(MenuItemData(menu_type=MenuItemType.PROFILE_ACTION_MENU, text='🔄 Обновить профиль (SyncProfile)', on_click=self._on_refresh_single_profile_click, icon='msg_sync', priority=110))
        self.add_menu_item(MenuItemData(menu_type=MenuItemType.PROFILE_ACTION_MENU, text='⭐ SyncProfile: Инфо о профиле', on_click=self._on_profile_menu_click, icon='msg_info', priority=100))
        self.add_menu_item(MenuItemData(menu_type=MenuItemType.MESSAGE_CONTEXT_MENU, text='🆔 Скопировать Emoji Document ID', on_click=self._on_copy_emoji_id_click, icon='msg_emoji', priority=50))

    def _on_refresh_single_profile_click(self, context: Dict[str, Any]):
        user = context.get('user')
        if not user:
            bulletins.show_error('Не удалось получить объект пользователя.')
            return
        user_id = int(getattr(user, 'id', 0) or 0)
        if user_id <= 0:
            bulletins.show_error('Неверный ID пользователя.')
            return

        def worker():
            server_url = self.get_setting('server_url', DEFAULT_SERVER_URL).rstrip('/')
            cookie_val = self.get_setting('custom_cookie', DEFAULT_SECRET_COOKIE).strip()
            try:
                url = f'{server_url}/api/profile/{user_id}'
                headers = {'User-Agent': f'SyncProfile/{__version__}', 'Cookie': f'{COOKIE_NAME}={cookie_val}'}
                req = urllib.request.Request(url, headers=headers)
                with urllib.request.urlopen(req, timeout=6) as resp:
                    if resp.status == 200:
                        resp_data = json.loads(resp.read().decode('utf-8'))
                        prof = resp_data.get('profile') or resp_data
                        if prof and 'user_id' in prof:
                            with self._sync_lock:
                                self._profiles_cache[user_id] = prof
                                self._cache_dirty = True
                            self._save_local_profiles_cache()
                            run_on_ui_thread(self._apply_all_to_all_accounts)
                            bulletins.show_success(f"✅ Профиль ID {user_id} обновлен!\nЦвет: #{prof.get('name_color')} | Обложка: #{prof.get('profile_color')}")
                            return
                bulletins.show_info(f'Профиль ID {user_id} не найден на сервере.')
            except Exception as e:
                logger.error(f'Ошибка обновления профиля {user_id}: {e}')
                bulletins.show_error(f'Ошибка загрузки профиля: {e}')
        threading.Thread(target=worker, daemon=True).start()

    def _on_profile_menu_click(self, context: Dict[str, Any]):
        user = context.get('user')
        if not user:
            bulletins.show_info('Не удалось получить объект пользователя.')
            return
        user_id = int(getattr(user, 'id', 0) or 0)
        profile = None
        with self._sync_lock:
            profile = self._profiles_cache.get(user_id)
        if profile:
            info = f"👤 ID: {user_id}\n⭐ Premium: {('Да' if profile.get('premium') else 'Нет')}\n🎨 Цвет имени/реплаев: #{profile.get('name_color', 0)} (узор: {profile.get('name_bg_emoji_id', 0)})\n🖼️ Цвет обложки: #{profile.get('profile_color', 0)} (узор: {profile.get('profile_bg_emoji_id', 0)})\n🆔 Эмодзи-статус ID: {profile.get('emoji_status_id', 'Нет')}"
            bulletins.show_info(f'SyncProfile активен:\n{info}')
        else:
            bulletins.show_info(f'Пользователь {user_id} не найден в локальной базе.')

    def _on_copy_emoji_id_click(self, context: Dict[str, Any]):
        message = context.get('message')
        if not message:
            bulletins.show_error('Сообщение не найдено.')
            return
        doc_ids = []
        try:
            msg_owner = getattr(message, 'messageOwner', None) or message
            if msg_owner and hasattr(msg_owner, 'entities'):
                entities = msg_owner.entities
                if entities:
                    cnt = entities.size() if hasattr(entities, 'size') else len(entities)
                    for i in range(cnt):
                        entity = entities.get(i) if hasattr(entities, 'get') else entities[i]
                        doc_id = getattr(entity, 'document_id', None)
                        if doc_id:
                            doc_ids.append(str(doc_id))
        except Exception:
            pass
        if doc_ids:
            found_id = doc_ids[0]
            self._copy_text_to_clipboard(found_id, f'Emoji ID скопирован: {found_id}')
        else:
            bulletins.show_info('В этом сообщении не найдено кастомных эмодзи.')

    def _copy_text_to_clipboard(self, text: str, success_msg: str=''):
        try:
            from org.telegram.messenger import AndroidUtilities
            AndroidUtilities.addToClipboard(text)
            if not success_msg:
                success_msg = f'Скопировано: {text}'
            bulletins.show_with_copy('Скопировано', text)
        except Exception:
            try:
                from android.content import Context, ClipData
                from org.telegram.messenger import ApplicationLoader
                ctx = getattr(ApplicationLoader, 'applicationContext', None)
                if ctx:
                    cm = ctx.getSystemService(Context.CLIPBOARD_SERVICE)
                    clip = ClipData.newPlainText('text', text)
                    cm.setPrimaryClip(clip)
            except Exception:
                pass
            bulletins.show_info(f'Скопировано: {text}')

    def create_settings(self) -> List[Any]:
        with self._sync_lock:
            total_cached = len(self._profiles_cache)
        items = [Header(text='Синхронизация профилей SyncProfile'), Switch(key='enable_sync', text='Включить SyncProfile', default=True, subtext='Отображать кастомные профили и цвета других пользователей плагина', icon='msg_sync'), Switch(key='enable_local_premium', text='Локальный Telegram Premium', default=True, subtext='Активировать встроенный локальный Premium', icon='msg_premium', on_change=lambda val: run_on_ui_thread(self._on_local_premium_toggle))]
        if ALLOW_CUSTOM_SERVER_CONFIG:
            items.extend([Input(key='server_url', text='URL сервера', default=DEFAULT_SERVER_URL, subtext='Адрес сервера (https://sync.efn.mom)', icon='msg_link'), Input(key='custom_cookie', text='Секретный токен Cookie', default=DEFAULT_SECRET_COOKIE, subtext='Ключ авторизации для доступа к sync.efn.mom', icon='msg_secret')])
        items.extend([Divider(text='Общие действия'), Text(text='⚡ Быстрая дельта-синхронизация', subtext='Запросить только новые и измененные профили с сервера (быстро и экономно)', icon='msg_sync', accent=True, on_click=lambda view: self.sync_delta_updates_from_server(show_bulletin=True)), Text(text='✨ Считать из Fake Premium для текущего аккаунта', subtext='Скопировать все цвета и эмодзи из Fake Premium в настройки', icon='msg_premium', accent=True, on_click=lambda view: self.grab_settings_from_fake_premium(-1, show_bulletin=True)), Text(text='🌐 Опубликовать ВСЕ мои аккаунты сразу', subtext='Отправить индивидуальные цвета всех аккаунтов на сервер в один клик', icon='msg_send', accent=True, on_click=lambda view: self.push_all_accounts(show_ui_bulletin=True)), Text(text=f'📥 Полное скачивание базы ({total_cached} в кэше)', subtext='Удалить старый локальный кэш и начисто скачать актуальную базу с сервера', icon='msg_download', accent=True, on_click=lambda view: self._interactive_sync_bottom_sheet())])
        active_accs = self._get_active_accounts_data()
        for acc_info in active_accs:
            acc_idx = acc_info.get('acc_idx', 0)
            uid = acc_info.get('user_id', 0)
            name = acc_info.get('name', f'Аккаунт {acc_idx + 1}')
            extra = acc_info.get('extra', '')
            is_curr = acc_info.get('is_current', False)
            curr_tag = ' [ТЕКУЩИЙ АКТИВНЫЙ]' if is_curr else ''
            section_title = f'👤 {name}{extra} (ID: {uid}){curr_tag}'
            default_name_c = 0
            default_prof_c = 0
            cur_prem = bool(self._get_slot_val(acc_idx, 'premium', True))
            cur_name_c = int(self._get_slot_val(acc_idx, 'name_color', default_name_c) or 0)
            cur_prof_c = int(self._get_slot_val(acc_idx, 'profile_color', default_prof_c) or 0)
            if cur_name_c < 0 or cur_name_c >= len(NAME_AND_REPLY_COLORS):
                cur_name_c = default_name_c
            if cur_prof_c < 0 or cur_prof_c >= len(PROFILE_COLORS):
                cur_prof_c = default_prof_c
            cur_name_bg = self._get_slot_val(acc_idx, 'name_bg_emoji_id', DEFAULT_NAME_BG_EMOJI) or ''
            cur_prof_bg = self._get_slot_val(acc_idx, 'profile_bg_emoji_id', DEFAULT_PROFILE_BG_EMOJI) or ''
            cur_em_id = self._get_slot_val(acc_idx, 'emoji_status_id', DEFAULT_EMOJI_STATUS_ID) or ''
            items.extend([Divider(text=section_title), Text(text=f'👁️ Предпросмотр профиля {name}', subtext='Посмотреть, как ваш профиль и сообщения видят другие', icon='msg_info', accent=True, on_click=lambda view, a=acc_idx: self._interactive_live_preview_dialog(a)), Text(text=f'✨ Считать из Fake Premium для {name}', subtext='Автоматически загрузить цвета и эмодзи из Fake Premium', icon='msg_premium', accent=True, on_click=lambda view, a=acc_idx: self.grab_settings_from_fake_premium(a, show_bulletin=True)), Text(text=f'🚀 Опубликовать профиль {name}', subtext=f'Отправить цвета и узоры для ID {uid} на сервер', icon='msg_send', accent=True, on_click=lambda view, a=acc_idx: self.push_specific_account(a, show_ui_bulletin=True)), Switch(key=f'slot_{acc_idx}_premium', text=f'Telegram Premium [{name}]', default=cur_prem, subtext=f'Отображать Premium-статус и звездочку для {name}', icon='msg_premium', on_change=lambda val: run_on_ui_thread(self._apply_all_to_all_accounts)), Selector(key=f'slot_{acc_idx}_name_color', text=f'Цвет имени и реплаев [{name}]', default=cur_name_c, items=NAME_AND_REPLY_COLORS, icon='msg_palette', on_change=lambda idx: run_on_ui_thread(self._apply_all_to_all_accounts)), Input(key=f'slot_{acc_idx}_name_bg_emoji_id', text=f'Узор имени и реплаев [{name}]', default=cur_name_bg, subtext='Document ID эмодзи-узора (оставьте пустым, если не нужен)', icon='msg_background'), Selector(key=f'slot_{acc_idx}_profile_color', text=f'Цвет обложки [{name}]', default=cur_prof_c, items=PROFILE_COLORS, icon='msg_theme', on_change=lambda idx: run_on_ui_thread(self._apply_all_to_all_accounts)), Input(key=f'slot_{acc_idx}_profile_bg_emoji_id', text=f'Узор обложки [{name}]', default=cur_prof_bg, subtext='ID эмодзи-узора (значки вокруг аватарки, оставьте пустым)', icon='msg_background'), Input(key=f'slot_{acc_idx}_emoji_status_id', text=f'Эмодзи-статус [{name}]', default=cur_em_id, subtext='ID эмодзи-статуса рядом с именем (оставьте пустым, если не нужен)', icon='msg_emoji')])
        items.extend([Divider(text='Действия'), Text(text='⭐ Активировать локальный Premium', subtext='Принудительно включить localPremium', icon='msg_premium', on_click=lambda view: (self._ensure_ayugram_premium(), bulletins.show_success('Локальный Premium активирован!'))), Text(text='🧹 Очистить локальный кэш', icon='msg_delete', red=True, on_click=self._interactive_clear_cache_dialog)])
        return items

    def _clear_cache_action(self, view: Any):
        with self._sync_lock:
            self._profiles_cache.clear()
            self._cache_dirty = False
        if self._json_cache_file:
            try:
                self._json_cache_file.wipe()
            except Exception:
                pass
        self._save_local_profiles_cache(force=True)
        bulletins.show_success('Локальный кэш очищен.')