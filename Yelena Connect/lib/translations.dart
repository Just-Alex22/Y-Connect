

import 'dart:ui';
import 'package:flutter/material.dart';
import 'package:shared_preferences/shared_preferences.dart';


const String kFallbackLang = 'en';

const Map<String, String> kLanguageNames = {
  'en': 'English',
  'es': 'Español',
  'pt': 'Português',
  'ca': 'Català',
  'de': 'Deutsch',
  'fr': 'Français',
  'ja': '日本語',
  'ko': '한국어',
  'it': 'Italiano',
  'tr': 'Türkçe',
  'ru': 'Русский',
};

const Map<String, String> kLanguageFlags = {
  'en': '🇬🇧',
  'es': '🇪🇸',
  'pt': '🇧🇷',
  'ca': '🇪🇸',
  'de': '🇩🇪',
  'fr': '🇫🇷',
  'ja': '🇯🇵',
  'ko': '🇰🇷',
  'it': '🇮🇹',
  'tr': '🇹🇷',
  'ru': '🇷🇺',
};


typedef Translations = Map<String, Map<String, String>>;

final Translations t = {

  'app_title': {
    'en': 'Y-Connect',
    'es': 'Y-Connect',
    'pt': 'Y-Connect',
    'ca': 'Y-Connect',
    'de': 'Y-Connect',
    'fr': 'Y-Connect',
    'ja': 'Y-Connect',
    'ko': 'Y-Connect',
    'it': 'Y-Connect',
    'tr': 'Y-Connect',
    'ru': 'Y-Connect',
  },


  'no_devices': {
    'en': 'No devices',
    'es': 'Sin dispositivos',
    'pt': 'Sem dispositivos',
    'ca': 'Sense dispositius',
    'de': 'Keine Geräte',
    'fr': 'Aucun appareil',
    'ja': 'デバイスなし',
    'ko': '기기 없음',
    'it': 'Nessun dispositivo',
    'tr': 'Cihaz yok',
    'ru': 'Нет устройств',
  },


  'card_connect': {
    'en': 'Connect',
    'es': 'Conectar',
    'pt': 'Conectar',
    'ca': 'Connectar',
    'de': 'Verbinden',
    'fr': 'Connexion',
    'ja': '接続',
    'ko': '연결',
    'it': 'Connetti',
    'tr': 'Bağlan',
    'ru': 'Подключение',
  },
  'card_status': {
    'en': 'Status',
    'es': 'Estado',
    'pt': 'Estado',
    'ca': 'Estat',
    'de': 'Status',
    'fr': 'État',
    'ja': 'ステータス',
    'ko': '상태',
    'it': 'Stato',
    'tr': 'Durum',
    'ru': 'Статус',
  },
  'card_media': {
    'en': 'Media',
    'es': 'Multimedia',
    'pt': 'Mídia',
    'ca': 'Multimèdia',
    'de': 'Medien',
    'fr': 'Média',
    'ja': 'メディア',
    'ko': '미디어',
    'it': 'Media',
    'tr': 'Medya',
    'ru': 'Медиа',
  },
  'card_notifications': {
    'en': 'Notifications',
    'es': 'Notificaciones',
    'pt': 'Notificações',
    'ca': 'Notificacions',
    'de': 'Benachrichtigungen',
    'fr': 'Notifications',
    'ja': '通知',
    'ko': '알림',
    'it': 'Notifiche',
    'tr': 'Bildirimler',
    'ru': 'Уведомления',
  },
  'card_files': {
    'en': 'Files',
    'es': 'Archivos',
    'pt': 'Arquivos',
    'ca': 'Fitxers',
    'de': 'Dateien',
    'fr': 'Fichiers',
    'ja': 'ファイル',
    'ko': '파일',
    'it': 'File',
    'tr': 'Dosyalar',
    'ru': 'Файлы',
  },
  'card_clipboard': {
    'en': 'Clipboard',
    'es': 'Portapapeles',
    'pt': 'Área de transferência',
    'ca': 'Portapapers',
    'de': 'Zwischenablage',
    'fr': 'Presse-papiers',
    'ja': 'クリップボード',
    'ko': '클립보드',
    'it': 'Appunti',
    'tr': 'Pano',
    'ru': 'Буфер обмена',
  },


  'scan_with_android': {
    'en': 'Scan with Y-Connect on Android',
    'es': 'Escanea con Y-Connect en Android',
    'pt': 'Escaneie com Y-Connect no Android',
    'ca': 'Escaneja amb Y-Connect a Android',
    'de': 'Scannen Sie mit Y-Connect auf Android',
    'fr': 'Scannez avec Y-Connect sur Android',
    'ja': 'AndroidのY-Connectでスキャン',
    'ko': 'Android에서 Y-Connect로 스캔',
    'it': 'Scansiona con Y-Connect su Android',
    'tr': 'Android\'de Y-Connect ile tarayın',
    'ru': 'Отсканируйте через Y-Connect на Android',
  },
  'connect_steps': {
    'en': '1. Open Y-Connect on Android\n2. Tap Connect\n3. Scan the QR',
    'es': '1. Abre Y-Connect en Android\n2. Toca Conectar\n3. Escanea el QR',
    'pt': '1. Abra o Y-Connect no Android\n2. Toque em Conectar\n3. Escaneie o QR',
    'ca': '1. Obre Y-Connect a Android\n2. Toca Connectar\n3. Escaneja el QR',
    'de': '1. Y-Connect auf Android öffnen\n2. Verbinden antippen\n3. QR scannen',
    'fr': '1. Ouvrir Y-Connect sur Android\n2. Appuyer sur Connexion\n3. Scanner le QR',
    'ja': '1. AndroidでY-Connectを開く\n2. 接続をタップ\n3. QRをスキャン',
    'ko': '1. Android에서 Y-Connect 열기\n2. 연결 탭\n3. QR 스캔',
    'it': '1. Apri Y-Connect su Android\n2. Tocca Connetti\n3. Scansiona il QR',
    'tr': '1. Android\'de Y-Connect\'i açın\n2. Bağlan\'a dokunun\n3. QR kodunu tarayın',
    'ru': '1. Откройте Y-Connect на Android\n2. Нажмите Подключить\n3. Отсканируйте QR',
  },
  'known_devices': {
    'en': 'Known devices',
    'es': 'Dispositivos conocidos',
    'pt': 'Dispositivos conhecidos',
    'ca': 'Dispositius coneguts',
    'de': 'Bekannte Geräte',
    'fr': 'Appareils connus',
    'ja': '既知のデバイス',
    'ko': '알려진 기기',
    'it': 'Dispositivi noti',
    'tr': 'Bilinen cihazlar',
    'ru': 'Известные устройства',
  },


  'battery': {
    'en': 'Battery',
    'es': 'Batería',
    'pt': 'Bateria',
    'ca': 'Bateria',
    'de': 'Akku',
    'fr': 'Batterie',
    'ja': 'バッテリー',
    'ko': '배터리',
    'it': 'Batteria',
    'tr': 'Pil',
    'ru': 'Батарея',
  },
  'charging': {
    'en': 'Charging',
    'es': 'Cargando',
    'pt': 'Carregando',
    'ca': 'Carregant',
    'de': 'Laden',
    'fr': 'En charge',
    'ja': '充電中',
    'ko': '충전 중',
    'it': 'In carica',
    'tr': 'Şarj oluyor',
    'ru': 'Зарядка',
  },
  'device_info': {
    'en': 'Device information',
    'es': 'Información del dispositivo',
    'pt': 'Informações do dispositivo',
    'ca': 'Informació del dispositiu',
    'de': 'Geräteinformationen',
    'fr': 'Informations sur l\'appareil',
    'ja': 'デバイス情報',
    'ko': '기기 정보',
    'it': 'Informazioni dispositivo',
    'tr': 'Cihaz bilgileri',
    'ru': 'Информация об устройстве',
  },
  'model': {
    'en': 'Model',
    'es': 'Modelo',
    'pt': 'Modelo',
    'ca': 'Model',
    'de': 'Modell',
    'fr': 'Modèle',
    'ja': 'モデル',
    'ko': '모델',
    'it': 'Modello',
    'tr': 'Model',
    'ru': 'Модель',
  },
  'android_label': {
    'en': 'Android',
    'es': 'Android',
    'pt': 'Android',
    'ca': 'Android',
    'de': 'Android',
    'fr': 'Android',
    'ja': 'Android',
    'ko': 'Android',
    'it': 'Android',
    'tr': 'Android',
    'ru': 'Android',
  },
  'network': {
    'en': 'Network',
    'es': 'Red',
    'pt': 'Rede',
    'ca': 'Xarxa',
    'de': 'Netzwerk',
    'fr': 'Réseau',
    'ja': 'ネットワーク',
    'ko': '네트워크',
    'it': 'Rete',
    'tr': 'Ağ',
    'ru': 'Сеть',
  },
  'signal': {
    'en': 'Signal',
    'es': 'Señal',
    'pt': 'Sinal',
    'ca': 'Senyal',
    'de': 'Signal',
    'fr': 'Signal',
    'ja': '信号',
    'ko': '신호',
    'it': 'Segnale',
    'tr': 'Sinyal',
    'ru': 'Сигнал',
  },


  'excellent': {
    'en': 'Excellent',
    'es': 'Excelente',
    'pt': 'Excelente',
    'ca': 'Excel·lent',
    'de': 'Ausgezeichnet',
    'fr': 'Excellent',
    'ja': '極好',
    'ko': '최상',
    'it': 'Eccellente',
    'tr': 'Mükemmel',
    'ru': 'Отлично',
  },
  'good': {
    'en': 'Good',
    'es': 'Bueno',
    'pt': 'Bom',
    'ca': 'Bo',
    'de': 'Gut',
    'fr': 'Bon',
    'ja': '良好',
    'ko': '양호',
    'it': 'Buono',
    'tr': 'İyi',
    'ru': 'Хорошо',
  },
  'fair': {
    'en': 'Fair',
    'es': 'Regular',
    'pt': 'Regular',
    'ca': 'Acceptable',
    'de': 'Mittelmäßig',
    'fr': 'Passable',
    'ja': '普通',
    'ko': '보통',
    'it': 'Sufficiente',
    'tr': 'Orta',
    'ru': 'Средне',
  },
  'poor': {
    'en': 'Poor',
    'es': 'Malo',
    'pt': 'Fraco',
    'ca': 'Dolent',
    'de': 'Schwach',
    'fr': 'Faible',
    'ja': '悪い',
    'ko': '나쁨',
    'it': 'Scarso',
    'tr': 'Zayıf',
    'ru': 'Плохо',
  },
  'unknown_quality': {
    'en': 'Unknown',
    'es': 'Desconocido',
    'pt': 'Desconhecido',
    'ca': 'Desconegut',
    'de': 'Unbekannt',
    'fr': 'Inconnu',
    'ja': '不明',
    'ko': '알 수 없음',
    'it': 'Sconosciuto',
    'tr': 'Bilinmiyor',
    'ru': 'Неизвестно',
  },


  'reconnecting': {
    'en': 'Reconnecting... attempt {a}',
    'es': 'Reconectando... intento {a}',
    'pt': 'Reconectando... tentativa {a}',
    'ca': 'Reconnectant... intent {a}',
    'de': 'Verbinde neu... Versuch {a}',
    'fr': 'Reconnexion... tentative {a}',
    'ja': '再接続中... {a}回目',
    'ko': '재연결 중... 시도 {a}',
    'it': 'Riconnessione... tentativo {a}',
    'tr': 'Yeniden bağlanıyor... deneme {a}',
    'ru': 'Переподключение... попытка {a}',
  },
  'reconnected': {
    'en': 'Reconnected',
    'es': 'Reconectado',
    'pt': 'Reconectado',
    'ca': 'Reconnectat',
    'de': 'Neu verbunden',
    'fr': 'Reconnecté',
    'ja': '再接続完了',
    'ko': '재연결됨',
    'it': 'Riconnesso',
    'tr': 'Yeniden bağlandı',
    'ru': 'Переподключено',
  },
  'could_not_reconnect': {
    'en': 'Could not reconnect',
    'es': 'No se pudo reconectar',
    'pt': 'Não foi possível reconectar',
    'ca': 'No s\'ha pogut reconnectar',
    'de': 'Neu verbinden fehlgeschlagen',
    'fr': 'Impossible de se reconnecter',
    'ja': '再接続できませんでした',
    'ko': '재연결할 수 없습니다',
    'it': 'Impossibile riconnettere',
    'tr': 'Yeniden bağlanılamadı',
    'ru': 'Не удалось переподключиться',
  },


  'phone_playback': {
    'en': 'Phone Playback',
    'es': 'Reproducción del teléfono',
    'pt': 'Reprodução do telefone',
    'ca': 'Reproducció del telèfon',
    'de': 'Telefon-Wiedergabe',
    'fr': 'Lecture du téléphone',
    'ja': '携帯の再生',
    'ko': '휴대폰 재생',
    'it': 'Riproduzione telefono',
    'tr': 'Telefon oynatma',
    'ru': 'Воспроизведение телефона',
  },
  'phone_volume': {
    'en': 'Phone Volume',
    'es': 'Volumen del teléfono',
    'pt': 'Volume do telefone',
    'ca': 'Volum del telèfon',
    'de': 'Telefon-Lautstärke',
    'fr': 'Volume du téléphone',
    'ja': '携帯の音量',
    'ko': '휴대폰 볼륨',
    'it': 'Volume telefono',
    'tr': 'Telefon sesi',
    'ru': 'Громкость телефона',
  },


  'no_notifications': {
    'en': 'No notifications',
    'es': 'Sin notificaciones',
    'pt': 'Sem notificações',
    'ca': 'Sense notificacions',
    'de': 'Keine Benachrichtigungen',
    'fr': 'Aucune notification',
    'ja': '通知なし',
    'ko': '알림 없음',
    'it': 'Nessuna notifica',
    'tr': 'Bildirim yok',
    'ru': 'Нет уведомлений',
  },


  'send_file': {
    'en': 'Send file',
    'es': 'Enviar archivo',
    'pt': 'Enviar arquivo',
    'ca': 'Enviar fitxer',
    'de': 'Datei senden',
    'fr': 'Envoyer le fichier',
    'ja': 'ファイル送信',
    'ko': '파일 보내기',
    'it': 'Invia file',
    'tr': 'Dosya gönder',
    'ru': 'Отправить файл',
  },
  'compress': {
    'en': 'Compress',
    'es': 'Comprimir',
    'pt': 'Comprimir',
    'ca': 'Comprimir',
    'de': 'Komprimieren',
    'fr': 'Compresser',
    'ja': '圧縮',
    'ko': '압축',
    'it': 'Comprimi',
    'tr': 'Sıkıştır',
    'ru': 'Сжать',
  },
  'transfer_history': {
    'en': 'Transfer history',
    'es': 'Historial de transferencias',
    'pt': 'Histórico de transferências',
    'ca': 'Historial de transferències',
    'de': 'Übertragungsverlauf',
    'fr': 'Historique des transferts',
    'ja': '転送履歴',
    'ko': '전송 기록',
    'it': 'Cronologia trasferimenti',
    'tr': 'Aktarım geçmişi',
    'ru': 'История передач',
  },
  'no_transfers': {
    'en': 'No transfers yet',
    'es': 'Sin transferencias',
    'pt': 'Sem transferências',
    'ca': 'Sense transferències',
    'de': 'Keine Übertragungen',
    'fr': 'Aucun transfert',
    'ja': '転送なし',
    'ko': '전송 없음',
    'it': 'Nessun trasferimento',
    'tr': 'Henüz aktarım yok',
    'ru': 'Нет передач',
  },


  'send_clipboard': {
    'en': 'Send clipboard to phone',
    'es': 'Enviar portapapeles al teléfono',
    'pt': 'Enviar área de transferência ao telefone',
    'ca': 'Enviar portapapers al telèfon',
    'de': 'Zwischenablage an Telefon senden',
    'fr': 'Envoyer le presse-papiers au téléphone',
    'ja': 'クリップボードを携帯に送信',
    'ko': '클립보드를 휴대폰으로 보내기',
    'it': 'Invia appunti al telefono',
    'tr': 'Panoyu telefona gönder',
    'ru': 'Отправить буфер обмена на телефон',
  },
  'received_from_phone': {
    'en': 'Received from phone',
    'es': 'Recibido del teléfono',
    'pt': 'Recebido do telefone',
    'ca': 'Rebut del telèfon',
    'de': 'Vom Telefon empfangen',
    'fr': 'Reçu du téléphone',
    'ja': '携帯から受信',
    'ko': '휴대폰에서 수신됨',
    'it': 'Ricevuto dal telefono',
    'tr': 'Telefondan alındı',
    'ru': 'Получено с телефона',
  },
  'nothing_received': {
    'en': 'Nothing received yet',
    'es': 'Nada recibido',
    'pt': 'Nada recebido',
    'ca': 'Res rebut',
    'de': 'Noch nichts empfangen',
    'fr': 'Rien reçu',
    'ja': 'まだ何も受信していません',
    'ko': '수신된 내용 없음',
    'it': 'Niente ricevuto',
    'tr': 'Henüz hiçbir şey alınmadı',
    'ru': 'Пока ничего не получено',
  },
  'send_text_to_phone': {
    'en': 'Send text to phone',
    'es': 'Enviar texto al teléfono',
    'pt': 'Enviar texto ao telefone',
    'ca': 'Enviar text al telèfon',
    'de': 'Text an Telefon senden',
    'fr': 'Envoyer du texte au téléphone',
    'ja': 'テキストを携帯に送信',
    'ko': '텍스트를 휴대폰으로 보내기',
    'it': 'Invia testo al telefono',
    'tr': 'Metni Telefona gönder',
    'ru': 'Отправить текст на телефон',
  },
  'type_text_hint': {
    'en': 'Type text...',
    'es': 'Escribe texto...',
    'pt': 'Digite o texto...',
    'ca': 'Escriu text...',
    'de': 'Text eingeben...',
    'fr': 'Tapez du texte...',
    'ja': 'テキストを入力...',
    'ko': '텍스트 입력...',
    'it': 'Digita testo...',
    'tr': 'Metin yazın...',
    'ru': 'Введите текст...',
  },


  'pairing_request': {
    'en': 'Pairing request',
    'es': 'Solicitud de emparejamiento',
    'pt': 'Solicitação de pareamento',
    'ca': 'Sol·licitud d\'emparellament',
    'de': 'Kopplungsanfrage',
    'fr': 'Demande d\'appairage',
    'ja': 'ペアリング要求',
    'ko': '페어링 요청',
    'it': 'Richiesta di associazione',
    'tr': 'Eşleştirme isteği',
    'ru': 'Запрос на сопряжение',
  },
  'wants_to_connect': {
    'en': '{name} ({ip}) wants to connect.',
    'es': '{name} ({ip}) quiere conectarse.',
    'pt': '{name} ({ip}) deseja conectar.',
    'ca': '{name} ({ip}) vol connectar.',
    'de': '{name} ({ip}) möchte eine Verbindung herstellen.',
    'fr': '{name} ({ip}) souhaite se connecter.',
    'ja': '{name} ({ip})が接続を求めています。',
    'ko': '{name} ({ip})이(가) 연결을 요청합니다.',
    'it': '{name} ({ip}) vuole connettersi.',
    'tr': '{name} ({ip}) bağlanmak istiyor.',
    'ru': '{name} ({ip}) хочет подключиться.',
  },
  'reject': {
    'en': 'Reject',
    'es': 'Rechazar',
    'pt': 'Rejeitar',
    'ca': 'Rebutjar',
    'de': 'Ablehnen',
    'fr': 'Refuser',
    'ja': '拒否',
    'ko': '거부',
    'it': 'Rifiuta',
    'tr': 'Reddet',
    'ru': 'Отклонить',
  },
  'accept_once': {
    'en': 'Accept once',
    'es': 'Aceptar una vez',
    'pt': 'Aceitar uma vez',
    'ca': 'Acceptar una vegada',
    'de': 'Einmal akzeptieren',
    'fr': 'Accepter une fois',
    'ja': '一度だけ許可',
    'ko': '한 번만 수락',
    'it': 'Accetta una volta',
    'tr': 'Bir kez kabul et',
    'ru': 'Принять один раз',
  },
  'trust_always': {
    'en': 'Trust always',
    'es': 'Confiar siempre',
    'pt': 'Confiar sempre',
    'ca': 'Confiar sempre',
    'de': 'Immer vertrauen',
    'fr': 'Toujours faire confiance',
    'ja': '常に信頼する',
    'ko': '항상 신뢰',
    'it': 'Fidati sempre',
    'tr': 'Her zaman güven',
    'ru': 'Всегда доверять',
  },


  'nearby_toast': {
    'en': '{name} is nearby',
    'es': '{name} está cerca',
    'pt': '{name} está por perto',
    'ca': '{name} és a prop',
    'de': '{name} ist in der Nähe',
    'fr': '{name} est à proximité',
    'ja': '{name}が近くにいます',
    'ko': '{name}이(가) 근처에 있습니다',
    'it': '{name} è nelle vicinanze',
    'tr': '{name} yakında',
    'ru': '{name} рядом',
  },


  'language': {
    'en': 'Language',
    'es': 'Idioma',
    'pt': 'Idioma',
    'ca': 'Idioma',
    'de': 'Sprache',
    'fr': 'Langue',
    'ja': '言語',
    'ko': '언어',
    'it': 'Lingua',
    'tr': 'Dil',
    'ru': 'Язык',
  },
  'auto_detect': {
    'en': 'Auto',
    'es': 'Auto',
    'pt': 'Auto',
    'ca': 'Auto',
    'de': 'Auto',
    'fr': 'Auto',
    'ja': '自動',
    'ko': '자동',
    'it': 'Auto',
    'tr': 'Otomatik',
    'ru': 'Авто',
  },
};


String tr(String key, {String lang = kFallbackLang, Map<String, String>? args}) {
  final entry = t[key];
  if (entry == null) return key;
  final value = entry[lang] ?? entry[kFallbackLang] ?? key;
  if (args != null) {
    String result = value;
    args.forEach((k, v) {
      result = result.replaceAll('{$k}', v);
    });
    return result;
  }
  return value;
}


class LanguageManager extends ChangeNotifier {
  static const _prefKey = 'app_language';

  String _currentLang = kFallbackLang;
  bool _autoDetect = true;

  LanguageManager() {
    _loadPrefs();
  }

  String get currentLang => _currentLang;
  bool get autoDetect => _autoDetect;


  String _detectSystemLang() {
    final locale = PlatformDispatcher.instance.locale;
    final code = locale.languageCode;


    if (kLanguageNames.containsKey(code)) return code;


    if (code.startsWith('pt')) return 'pt';
    if (code.startsWith('ca')) return 'ca';

    return kFallbackLang;
  }

  String get effectiveLang {
    if (_autoDetect) return _detectSystemLang();
    return _currentLang;
  }


  String translate(String key, {Map<String, String>? args}) {
    return tr(key, lang: effectiveLang, args: args);
  }

  Future<void> _loadPrefs() async {
    final prefs = await SharedPreferences.getInstance();
    final saved = prefs.getString(_prefKey);
    if (saved != null && saved.startsWith('auto:')) {
      _autoDetect = true;
      _currentLang = saved.substring(5);
    } else if (saved != null && kLanguageNames.containsKey(saved)) {
      _autoDetect = false;
      _currentLang = saved;
    } else {

      _autoDetect = true;
      _currentLang = _detectSystemLang();
    }
    notifyListeners();
  }

  Future<void> setLanguage(String code) async {
    if (!kLanguageNames.containsKey(code)) return;
    _autoDetect = false;
    _currentLang = code;
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString(_prefKey, code);
    notifyListeners();
  }

  Future<void> setAutoDetect() async {
    _autoDetect = true;
    _currentLang = _detectSystemLang();
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString(_prefKey, 'auto:$_currentLang');
    notifyListeners();
  }
}


class LanguageSelectorButton extends StatelessWidget {
  final LanguageManager langMgr;
  const LanguageSelectorButton({required this.langMgr, super.key});

  @override
  Widget build(BuildContext context) {
    return ListenableBuilder(
      listenable: langMgr,
      builder: (context, _) {
        final flag = kLanguageFlags[langMgr.effectiveLang] ?? '';
        final name = langMgr.autoDetect
            ? '${kLanguageNames[langMgr.effectiveLang] ?? 'Auto'}'
            : kLanguageNames[langMgr.effectiveLang] ?? '';

        return PopupMenuButton<String>(
          tooltip: langMgr.translate('language'),
          offset: const Offset(0, 40),
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(10),
            side: const BorderSide(color: Color(0xFF383838)),
          ),
          color: const Color(0xFF2e2e2e),
          onSelected: (val) {
            if (val == 'auto') {
              langMgr.setAutoDetect();
            } else {
              langMgr.setLanguage(val);
            }
          },
          itemBuilder: (ctx) {
            final items = <PopupMenuEntry<String>>[];


            items.add(PopupMenuItem<String>(
              value: 'auto',
              child: Row(
                children: [
                  const Icon(Icons.language, size: 16, color: Color(0xFF9a9996)),
                  const SizedBox(width: 8),
                  Text(
                    'Auto: ${kLanguageNames[langMgr._detectSystemLang()] ?? ''}',
                    style: const TextStyle(fontSize: 12, color: Color(0xFFc0bfb8)),
                  ),
                  if (langMgr.autoDetect) ...[
                    const Spacer(),
                    const Icon(Icons.check, size: 14, color: Color(0xFF5a7a22)),
                  ],
                ],
              ),
            ));

            items.add(const PopupMenuDivider(height: 4));


            for (final code in kLanguageNames.keys) {
              items.add(PopupMenuItem<String>(
                value: code,
                child: Row(
                  children: [
                    Text(kLanguageFlags[code] ?? '', style: const TextStyle(fontSize: 14)),
                    const SizedBox(width: 8),
                    Text(
                      kLanguageNames[code] ?? code,
                      style: const TextStyle(fontSize: 12, color: Color(0xFFc0bfb8)),
                    ),
                    if (!langMgr.autoDetect && langMgr.currentLang == code) ...[
                      const Spacer(),
                      const Icon(Icons.check, size: 14, color: Color(0xFF5a7a22)),
                    ],
                  ],
                ),
              ));
            }
            return items;
          },
          child: Container(
            padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
            decoration: BoxDecoration(
              borderRadius: BorderRadius.circular(6),
              border: Border.all(color: const Color(0xFF383838)),
            ),
            child: Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                Text(flag, style: const TextStyle(fontSize: 13)),
                const SizedBox(width: 4),
                Text(name, style: const TextStyle(fontSize: 11, color: Color(0xFF9a9996))),
                const SizedBox(width: 4),
                Icon(Icons.arrow_drop_down, size: 14, color: const Color(0xFF9a9996)),
              ],
            ),
          ),
        );
      },
    );
  }
}


