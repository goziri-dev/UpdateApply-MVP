import 'package:dio/dio.dart';
import 'package:scoped_deps/scoped_deps.dart';
import 'package:signals/signals_flutter.dart';

import '../services/billing_service.dart';

final billingBalanceRef = create(() => signal<BillingBalance?>(null));
final billingBalanceLoadingRef = create(() => signal(false));
final billingBalanceErrorRef = create(() => signal<String?>(null));

/// Soft nudge dismissed for this app session (1 credit left).
final billingNudgeDismissedRef = create(() => signal(false));

Signal<BillingBalance?>? _balanceFallback;
Signal<bool>? _loadingFallback;
Signal<String?>? _errorFallback;
Signal<bool>? _nudgeFallback;

Signal<BillingBalance?> get billingBalance =>
    read(billingBalanceRef, orElse: () => _balanceFallback ??= signal(null));

Signal<bool> get billingBalanceLoading => read(
  billingBalanceLoadingRef,
  orElse: () => _loadingFallback ??= signal(false),
);

Signal<String?> get billingBalanceError =>
    read(billingBalanceErrorRef, orElse: () => _errorFallback ??= signal(null));

Signal<bool> get billingNudgeDismissed => read(
  billingNudgeDismissedRef,
  orElse: () => _nudgeFallback ??= signal(false),
);

bool get hasOneCreditLeft {
  final bal = billingBalance.value;
  return bal != null && bal.creditBalance == 1;
}

bool get hasZeroCredits {
  final bal = billingBalance.value;
  return bal != null && bal.creditBalance <= 0;
}

void dismissBillingNudge() {
  billingNudgeDismissed.value = true;
}

Future<void> refreshBillingBalance({BillingService? service}) async {
  final api = service ?? BillingService();
  billingBalanceLoading.value = true;
  billingBalanceError.value = null;
  try {
    final bal = await api.getBalance();
    billingBalance.value = bal;
  } on DioException catch (e) {
    billingBalanceError.value = _dioMessage(e);
  } on Object catch (e) {
    billingBalanceError.value = '$e';
  } finally {
    billingBalanceLoading.value = false;
  }
}

String _dioMessage(DioException e) {
  final data = e.response?.data;
  if (data is Map) {
    final detail = data['detail'];
    if (detail is Map && detail['message'] is String) {
      return detail['message'] as String;
    }
    if (detail is String) return detail;
  }
  return e.message ?? 'Could not load balance';
}

/// True when tailor 402 (or structured insufficient_credits) should open paywall.
bool isInsufficientCreditsError(DioException error) {
  if (error.response?.statusCode == 402) return true;
  final data = error.response?.data;
  if (data is! Map) return false;
  final detail = data['detail'];
  if (detail is Map) {
    return detail['error'] == 'insufficient_credits';
  }
  return false;
}

String messageFromBillingDio(DioException e) {
  final data = e.response?.data;
  if (data is Map) {
    final detail = data['detail'];
    if (detail is Map) {
      final message = detail['message'];
      if (message is String && message.isNotEmpty) return message;
      final msg = detail['msg'];
      if (msg is String && msg.isNotEmpty) return msg;
    }
    if (detail is String) return detail;
    if (detail is List && detail.isNotEmpty) {
      final first = detail.first;
      if (first is Map && first['msg'] is String) {
        return first['msg'] as String;
      }
    }
  }
  return e.message ?? 'Request failed';
}
