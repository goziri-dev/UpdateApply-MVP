import 'package:dio/dio.dart';

import '../../../services/api_client.dart';

/// Stripe Checkout / balance API (server owns secrets; client only opens URLs).
class BillingService {
  BillingService({ApiClient? client}) : _client = client ?? apiClient;

  final ApiClient _client;

  Dio get _dio => _client.dio;

  Future<BillingBalance> getBalance() async {
    final response = await _dio.get<Map<String, dynamic>>(
      '/api/v1/billing/balance',
    );
    return BillingBalance.fromJson(response.data ?? {});
  }

  Future<CheckoutSession> createCheckout(String plan) async {
    final response = await _dio.post<Map<String, dynamic>>(
      '/api/v1/billing/checkout',
      data: {'plan': plan},
    );
    return CheckoutSession.fromJson(response.data ?? {});
  }

  Future<String> createPortal() async {
    final response = await _dio.post<Map<String, dynamic>>(
      '/api/v1/billing/portal',
    );
    final url = response.data?['portal_url'];
    if (url is! String || url.isEmpty) {
      throw StateError('Portal URL missing from server response');
    }
    return url;
  }
}

class BillingBalance {
  const BillingBalance({
    required this.creditBalance,
    required this.freeGrantApplied,
    this.stripeCustomerId,
  });

  final int creditBalance;
  final bool freeGrantApplied;
  final String? stripeCustomerId;

  factory BillingBalance.fromJson(Map<String, dynamic> json) {
    return BillingBalance(
      creditBalance: (json['credit_balance'] as num?)?.toInt() ?? 0,
      freeGrantApplied: json['free_grant_applied'] == true,
      stripeCustomerId: json['stripe_customer_id'] as String?,
    );
  }
}

class CheckoutSession {
  const CheckoutSession({
    required this.checkoutUrl,
    required this.sessionId,
    required this.plan,
  });

  final String checkoutUrl;
  final String sessionId;
  final String plan;

  factory CheckoutSession.fromJson(Map<String, dynamic> json) {
    final url = json['checkout_url'];
    final id = json['session_id'];
    final plan = json['plan'];
    if (url is! String || url.isEmpty) {
      throw StateError('Checkout URL missing from server response');
    }
    return CheckoutSession(
      checkoutUrl: url,
      sessionId: id is String ? id : '',
      plan: plan is String ? plan : '',
    );
  }
}
