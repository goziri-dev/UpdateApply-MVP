import 'package:web/web.dart' as web;

/// Live browser location — includes `?code=` even when a hash route is present.
Uri currentAuthCallbackUri() => Uri.parse(web.window.location.href);
