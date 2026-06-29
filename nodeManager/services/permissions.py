from functools import wraps

from django.http import HttpResponseForbidden, HttpResponseRedirect

from loginSystem.models import Administrator
from websiteFunctions.models import ChildDomains, Websites

from .users import list_owned_domains, list_reseller_domains


def get_current_cyberpanel_user(request):
    user_id = request.session.get("userID")
    if user_id:
        return Administrator.objects.get(pk=user_id)
    if getattr(request, "user", None) and request.user.is_authenticated:
        return Administrator.objects.get(userName=request.user.username)
    raise Administrator.DoesNotExist


def is_admin(user):
    return int(getattr(user, "type", 0)) == 1 or getattr(user, "userName", "") == "admin"


def is_reseller(user):
    return int(getattr(user, "type", 0)) == 2


def get_domains_for_user(user):
    if is_admin(user):
        websites = Websites.objects.filter(state=1).order_by("domain")
        domains = [item.domain for item in websites]
        domains.extend(list(ChildDomains.objects.order_by("domain").values_list("domain", flat=True)))
        return domains
    if is_reseller(user):
        return sorted(set(list_owned_domains(user) + list_reseller_domains(user)))
    return list_owned_domains(user)


def can_manage_domain(user, domain):
    if is_admin(user):
        return Websites.objects.filter(domain=domain).exists() or ChildDomains.objects.filter(domain=domain).exists()
    return domain in set(get_domains_for_user(user))


def can_manage_node_app(user, app):
    if is_admin(user):
        return True
    if int(app.owner_user_id) == int(user.pk):
        return True
    if is_reseller(user):
        return can_manage_domain(user, app.domain)
    return False


def can_view_node_app(user, app):
    return can_manage_node_app(user, app)


def can_view_logs(user, app):
    return can_view_node_app(user, app)


def cyberpanel_login_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        try:
            get_current_cyberpanel_user(request)
        except Exception:
            return HttpResponseRedirect("/")
        return view_func(request, *args, **kwargs)

    return wrapper


def cyberpanel_admin_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        try:
            user = get_current_cyberpanel_user(request)
        except Exception:
            return HttpResponseRedirect("/")
        if not is_admin(user):
            return HttpResponseForbidden("Admin privileges required.")
        return view_func(request, *args, **kwargs)

    return wrapper
