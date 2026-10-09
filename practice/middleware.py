class SecurityHeadersMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        response['Content-Security-Policy'] = "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'; font-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'; form-action 'self' https://accounts.google.com"
        response['Permissions-Policy'] = 'camera=(), microphone=(), geolocation=()'
        response['Cache-Control'] = 'no-store' if request.user.is_authenticated or request.path.startswith(('/api/', '/accounts/')) else 'no-cache'
        return response
