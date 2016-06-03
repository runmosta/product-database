import json
import logging
from datetime import datetime
from app.ciscoeox.exception import CredentialsNotFoundException, ConnectionFailedException, CiscoApiCallFailed
from app.ciscoeox.base_api import CiscoEoxApi
from app.config import AppSettings
from app.config.utils import test_cisco_eox_api_access
from app.productdb.models import Product, Vendor

logger = logging.getLogger(__name__)


def convert_time_format(date_format):
    """
    helper function to convert the data format that is used by the Cisco EoX API
    :param date_format:
    :return:
    """
    if date_format == "YYYY-MM-DD":
        return "%Y-%m-%d"

    return "%Y-%m-%d"


def update_local_db_based_on_record(eox_record, create_missing=False):
    """
    Update a database record based on a Cisco EoX API call

    :param eox_record: JSON data from the Cisco EoX API
    :param create_missing: set to True, if the product should be created if it doesn't exist in the local database
    :return:
    """
    pid = eox_record['EOLProductID']
    result_msg = ""
    created = False

    if create_missing:
        product, created = Product.objects.get_or_create(product_id=pid)
        if created:
            logger.info("Product '%s' was not in database and is created" % pid)
            product.product_id = pid
            product.description = eox_record['ProductIDDescription']
            # it is a Cisco API and the vendors are read-only within the database
            product.vendor = Vendor.objects.get(name="Cisco Systems")
            created = True
    else:
        try:
            product = Product.objects.get(product_id=pid)

        except Exception:
            logger.debug("product not found in database: %s" % pid, exc_info=True)
            result_msg = "%s: product not found in local database" % pid.ljust(20)
            return result_msg

    # update the lifecycle information
    try:
        update = True
        if product.eox_update_time_stamp is None:
            logger.info("Update product %s because of missing timestamps" % pid)
            result_msg = "%s: data updated (created: %s)" % (pid.ljust(20), created)

        else:
            date_format = convert_time_format(eox_record['UpdatedTimeStamp']['dateFormat'])
            updated_time_stamp = datetime.strptime(eox_record['UpdatedTimeStamp']['value'],
                                                   date_format).date()
            if product.eox_update_time_stamp >= updated_time_stamp:
                logger.debug("update of product not required: %s >= %s " % (product.eox_update_time_stamp,
                                                                            updated_time_stamp))
                update = False

            else:
                logger.info("Product %s update required" % pid)
                result_msg = "%s: data updated (created: %s)" % (pid.ljust(20), created)

        if update:
            if "UpdatedTimeStamp" in eox_record.keys():
                value = eox_record['UpdatedTimeStamp']['value']
                if value != " ":
                    euts = datetime.strptime(value,
                                             convert_time_format(
                                                 eox_record['UpdatedTimeStamp']['dateFormat']
                                             )).date()
                    product.eox_update_time_stamp = euts

            if "EndOfSaleDate" in eox_record.keys():
                value = eox_record['EndOfSaleDate']['value']
                if value != " ":
                    eosd = datetime.strptime(value,
                                             convert_time_format(
                                                 eox_record['EndOfSaleDate']['dateFormat']
                                             )).date()
                    product.end_of_sale_date = eosd

            if "LastDateOfSupport" in eox_record.keys():
                value = eox_record['LastDateOfSupport']['value']
                if value != " ":
                    print("Before: %s" % value)
                    eosud = datetime.strptime(value,
                                              convert_time_format(
                                                  eox_record['LastDateOfSupport']['dateFormat']
                                              )).date()
                    print("After: %s" % eosud)
                    product.end_of_support_date = eosud

            if "EOXExternalAnnouncementDate" in eox_record.keys():
                value = eox_record['EOXExternalAnnouncementDate']['value']
                if value != " ":
                    eead = datetime.strptime(value,
                                             convert_time_format(
                                                 eox_record['EOXExternalAnnouncementDate']['dateFormat']
                                             )).date()
                    product.eol_ext_announcement_date = eead

            if "EndOfSWMaintenanceReleases" in eox_record.keys():
                value = eox_record['EndOfSWMaintenanceReleases']['value']
                if value != " ":
                    eosmd = datetime.strptime(value,
                                              convert_time_format(
                                                  eox_record['EndOfSWMaintenanceReleases']['dateFormat']
                                              )).date()
                    product.end_of_sw_maintenance_date = eosmd

            if "EndOfRoutineFailureAnalysisDate" in eox_record.keys():
                value = eox_record['EndOfRoutineFailureAnalysisDate']['value']
                if value != " ":
                    eorfa_date = datetime.strptime(value,
                                                   convert_time_format(
                                                       eox_record['EndOfRoutineFailureAnalysisDate']['dateFormat']
                                                   )).date()
                    product.end_of_routine_failure_analysis = eorfa_date

            if "EndOfServiceContractRenewal" in eox_record.keys():
                value = eox_record['EndOfServiceContractRenewal']['value']
                if value != " ":
                    eoscr = datetime.strptime(value,
                                              convert_time_format(
                                                  eox_record['EndOfServiceContractRenewal']['dateFormat']
                                              )).date()
                    product.end_of_service_contract_renewal = eoscr

            if "EndOfSvcAttachDate" in eox_record.keys():
                value = eox_record['EndOfSvcAttachDate']['value']
                if value != " ":
                    eonsa = datetime.strptime(value,
                                              convert_time_format(
                                                  eox_record['EndOfSvcAttachDate']['dateFormat']
                                              )).date()
                    product.end_of_new_service_attachment_date = eonsa

            if "EndOfSecurityVulSupportDate" in eox_record.keys():
                value = eox_record['EndOfSecurityVulSupportDate']['value']
                if value != " ":
                    eovsd = datetime.strptime(value,
                                              convert_time_format(
                                                  eox_record['EndOfSecurityVulSupportDate']['dateFormat']
                                              )).date()
                    product.end_of_sec_vuln_supp_date = eovsd

            if "ProductBulletinNumber" in eox_record.keys():
                product.eol_reference_number = eox_record['ProductBulletinNumber']

            if "LinkToProductBulletinURL" in eox_record.keys():
                product.eol_reference_url = eox_record['LinkToProductBulletinURL']

            product.save()

    except Exception as ex:
        logger.error("update of product '%s' failed." % pid, exc_info=True)
        logger.debug("DataSet with exception\n%s" % json.dumps(eox_record, indent=4))
        result_msg = "%s: ...Failed (%s, see log for details)" % (pid.ljust(20), ex)
        return result_msg

    return result_msg


def query_cisco_eox_api(query_string, blacklist, create_missing=False):
    """
    execute a query against the Cisco API and updates the database if the product
    is not defined in the blacklist string.

    :param query_string: string that should be used against the Cisco EoX API
    :param blacklist: list of strings that shouldn't be imported to the database
    :param create_missing:
    :return:
    """
    eoxapi = CiscoEoxApi()
    eoxapi.load_client_credentials()
    results = []

    try:
        max_pages = 999
        current_page = 1
        result_pages = 0

        while current_page <= max_pages:
            logger.info("Executing API query '%s' on page '%d" % (query_string, current_page))
            eoxapi.query_product(product_id=query_string, page=current_page)
            if current_page == 1:
                result_pages = eoxapi.amount_of_pages()
                logger.info("Initial query returns %d page(s)" % result_pages)

            records = eoxapi.get_eox_records()

            # check for errors
            if eoxapi.has_error(records[0]):
                logger.info("Query '%s' returns no valid values: %s" % (query_string,
                                                                        eoxapi.get_error_description(records[0])))
            else:
                # check that the query has valid results
                if eoxapi.get_valid_record_count() > 0:
                    # processing records
                    for record in records:
                        # check if record is product of the blacklist
                        pid = record['EOLProductID']
                        logger.info("processing product '%s'..." % pid)
                        if pid not in blacklist:
                            res = update_local_db_based_on_record(record, create_missing)
                            results.append(res)

                        else:
                            logger.info("Product '%s' blacklisted... no further processing" % pid)
                            results.append("%s: blacklisted entry (not updated)" % pid.ljust(20))
                else:
                    logger.warn("Query '%s' returns no valid values" % query_string)

            if current_page == result_pages:
                break

            else:
                current_page += 1

    except ConnectionFailedException:
        logger.error("connection for query failed: %s" % query_string, exc_info=True)
        raise

    except CiscoApiCallFailed:
        logger.fatal("query failed: %s" % query_string, exc_info=True)
        raise

    return results


def update_cisco_eox_database(api_query=None):
    """
    Synchronizes the local EoX data from the Cisco EoX API using the specified queries or the queries specified in the
    configuration when api_query is set to None

    :param api_query: query to execute against the Cisco EoX API, if None than the settings parameters are executed
    :return:
    """
    # load application settings and check, that the API is enabled
    app_settings = AppSettings()
    app_settings.read_file()

    if not app_settings.is_cisco_api_enabled():
        msg = "Cisco API access not enabled"
        logger.warn(msg)
        raise CiscoApiCallFailed(msg)

    # test API access
    success = test_cisco_eox_api_access(
        app_settings.get_cisco_api_client_id(),
        app_settings.get_cisco_api_client_secret(),
        False
    )

    if not success:
        msg = "Cisco API not configured correctly, credentials not valid"
        logger.error(msg)
        raise CredentialsNotFoundException(msg)

    # create a list with all queries that should be executed
    if api_query is None:
        queries = app_settings.get_cisco_eox_api_queries().splitlines()

    else:
        queries = [api_query]

    blacklist = app_settings.get_product_blacklist_regex().split(";")
    create_missing = app_settings.is_auto_create_new_products()
    query_results = []

    # start with Cisco EoX API queries
    for query in queries:
        logger.info("Query EoX database: %s" % query)
        res = query_cisco_eox_api(query, blacklist, create_missing)
        query_results.extend(res)

    # filter empty result strings
    final_query_results = []
    for q in query_results:
        if q != "":
            final_query_results.append(q)

    if len(final_query_results) == 0:
        final_query_results.append("No product update required")

    return final_query_results


def synchronize_with_cisco_eox_api(api_query=None):
    """
    execute the Cisco EoX state synchronization if configured and enabled

    :param api_query: query to execute against the Cisco EoX API, if None than the settings parameters are executed
    :return:
    """
    app_settings = AppSettings()
    app_settings.read_file()

    # update based on the configured query settings
    if app_settings.is_cisco_api_enabled():
        # create a list with all queries that should be executed
        if api_query:
            result = update_cisco_eox_database(api_query=api_query)

        else:
            result = update_cisco_eox_database()

        # write execution results and set timestamp
        result_msg = ""
        for r in result:
            result_msg += r + "\n"

        app_settings.set_cisco_eox_api_auto_sync_last_execution_time(datetime.now())
        app_settings.set_cisco_eox_api_auto_sync_last_execution_result(result_msg)
        app_settings.write_file()

        return result

    else:
        return {"msg:": "Cisco EoX API not enabled or no queries configured"}