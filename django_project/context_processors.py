"""
custom context processors for the page
"""
from django_auth_ldap.backend import LDAPBackend
from django.conf import settings

from app.config.settings import AppSettings


def is_debug_enabled(request):
    request_ip = None
    if settings.DEBUG:
        request_ip = "forward: %s; remote: %s" % (request.META.get('HTTP_X_FORWARDED_FOR', None), request.META.get('REMOTE_ADDR'))

    return {
        "DEBUG_MODE": settings.DEBUG,
        "REQUEST_IP": request_ip
    }


def is_ldap_authenticated_user(request):
    """
    injects an IS_LDAP_ACCOUNT
    """
    result = False
    try:
        if settings.LDAP_ENABLE:
            # try to get the username
            user = LDAPBackend().populate_user(request.user.get_username())

            # try to access the ldap_username (if this raises an exception, the user is not an LDAP user)
            val = user.ldap_username
            result = True

    except Exception as ex:
        # cannot get user info, assume that this is not an LDAP account
        pass

    return {
        "IS_LDAP_ACCOUNT": result
    }


def get_internal_product_id_label(request):
    app_config = AppSettings()
    return {
        "INTERNAL_PRODUCT_ID_LABEL": app_config.get_internal_product_id_label(),
        "STAT_AMOUNT_OF_PRODUCT_CHECKS": app_config.get_amount_of_product_checks(),
        "STAT_AMOUNT_OF_UNIQUE_PRODUCT_CHECK_ENTRIES": app_config.get_amount_of_unique_product_check_entries()
    }
