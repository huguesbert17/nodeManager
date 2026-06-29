from websiteFunctions.models import ChildDomains, Websites


def get_primary_website(domain):
    try:
        return Websites.objects.get(domain=domain)
    except Websites.DoesNotExist:
        child = ChildDomains.objects.select_related("master").get(domain=domain)
        return child.master


def get_website_home(website):
    return "/home/%s" % website.domain


def get_app_base_dir(website):
    return "%s/nodejs" % get_website_home(website)


def get_linux_user(website):
    return website.externalApp


def list_owned_domains(admin):
    websites = Websites.objects.filter(admin=admin, state=1).order_by("domain")
    domains = [item.domain for item in websites]
    child_domains = ChildDomains.objects.filter(master__admin=admin).select_related("master").order_by("domain")
    domains.extend([item.domain for item in child_domains])
    return domains


def list_reseller_domains(admin):
    from loginSystem.models import Administrator

    child_admin_ids = list(Administrator.objects.filter(owner=admin.pk).values_list("pk", flat=True))
    websites = Websites.objects.filter(admin_id__in=child_admin_ids, state=1).order_by("domain")
    domains = [item.domain for item in websites]
    child_domains = ChildDomains.objects.filter(master__admin_id__in=child_admin_ids).order_by("domain")
    domains.extend([item.domain for item in child_domains])
    return domains
