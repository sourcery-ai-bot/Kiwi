# -*- coding: utf-8 -*-

from django.utils.dateparse import parse_duration
from django.forms import EmailField, ValidationError

from modernrpc.core import rpc_method, REQUEST_KEY

from tcms.core.utils import string_to_list, form_errors_to_list
from tcms.management.models import Tag
from tcms.management.models import Component
from tcms.testcases.models import TestCase
from tcms.xmlrpc.forms import UpdateCaseForm, NewCaseForm

from tcms.xmlrpc.decorators import permissions_required


__all__ = (
    'create',
    'update',
    'filter',

    'add_component',
    'get_components',
    'remove_component',

    'add_notification_cc',
    'get_notification_cc',
    'remove_notification_cc',

    'add_tag',
    'remove_tag',
)


@permissions_required('testcases.add_testcasecomponent')
@rpc_method(name='TestCase.add_component')
def add_component(case_id, component_id):
    """
    .. function:: XML-RPC TestCase.add_component(case_id, component_id)

        Add component to the selected test case.

        :param case_id: PK of TestCase to modify
        :type case_id: int
        :param component_id: PK of Component to add
        :type component_id: int
        :return: None
        :raises: PermissionDenied if missing the *testcases.add_testcasecomponent*
                 permission
        :raises: DoesNotExist if missing test case or component that match the
                 specified PKs
    """
    TestCase.objects.get(pk=case_id).add_component(
        Component.objects.get(pk=component_id)
    )


@rpc_method(name='TestCase.get_components')
def get_components(case_id):
    """
    .. function:: XML-RPC TestCase.get_components(case_id)

        Get the list of components attached to this case.

        :param case_id: PK if TestCase
        :type case_id: int
        :return: Serialized list of :class:`tcms.management.models.Component` objects
        :rtype: list(dict)
        :raises: TestCase.DoesNotExist if missing test case matching PK
    """
    test_case = TestCase.objects.get(case_id=case_id)

    component_ids = test_case.component.values_list('id', flat=True)
    query = {'id__in': component_ids}
    return Component.to_xmlrpc(query)


@permissions_required('testcases.delete_testcasecomponent')
@rpc_method(name='TestCase.remove_component')
def remove_component(case_id, component_id):
    """
    .. function:: XML-RPC TestCase.remove_component(case_id, component_id)

        Remove selected component from the selected test case.

        :param case_id: PK of TestCase to modify
        :type case_id: int
        :param component_id: PK of Component to remove
        :type component_id: int
        :return: None
        :raises: PermissionDenied if missing the *testcases.delete_testcasecomponent*
                 permission
        :raises: DoesNotExist if missing test case or component that match the
                 specified PKs
    """
    TestCase.objects.get(pk=case_id).remove_component(
        Component.objects.get(pk=component_id)
    )


def _validate_cc_list(cc_list):
    """
        Validate each email address given in argument. Called by
        notification RPC methods.

        :param cc_list: List of email addresses
        :type cc_list: list
        :return: None
        :raises: TypeError or ValidationError if addresses are not valid.
    """

    if not isinstance(cc_list, list):
        raise TypeError('cc_list should be a list object.')

    field = EmailField(required=True)
    invalid_emails = []

    for item in cc_list:
        try:
            field.clean(item)
        except ValidationError:
            invalid_emails.append(item)

    if invalid_emails:
        raise ValidationError(
            field.error_messages['invalid'] % {
                'value': ', '.join(invalid_emails)})


@permissions_required('testcases.change_testcase')
@rpc_method(name='TestCase.add_notification_cc')
def add_notification_cc(case_id, cc_list):
    """
    .. function:: XML-RPC TestCase.add_notification_cc(case_id, cc_list)

        Add email addresses to the notification list of specified TestCase

        :param case_id: PK of TestCase to be modified
        :param case_id: int
        :param cc_list: List of email addresses
        :type cc_list: list(str)
        :return: None
        :raises: TypeError or ValidationError if email validation fails
        :raises: PermissionDenied if missing *testcases.change_testcase* permission
        :raises: TestCase.DoesNotExist if object with case_id doesn't exist
    """

    _validate_cc_list(cc_list)

    test_case = TestCase.objects.get(pk=case_id)

    # First, find those that do not exist yet.
    existing_cc = test_case.emailing.get_cc_list()
    adding_cc = list(set(cc_list) - set(existing_cc))

    # add the ones which are new
    test_case.emailing.add_cc(adding_cc)


@permissions_required('testcases.change_testcase')
@rpc_method(name='TestCase.remove_notification_cc')
def remove_notification_cc(case_id, cc_list):
    """
    .. function:: XML-RPC TestCase.remove_notification_cc(case_id, cc_list)

        Remove email addresses from the notification list of specified TestCase

        :param case_id: PK of TestCase to modify
        :type case_id: int
        :param cc_list: List of email addresses
        :type cc_list: list(str)
        :return: None
        :raises: TypeError or ValidationError if email validation fails
        :raises: PermissionDenied if missing *testcases.change_testcase* permission
        :raises: TestCase.DoesNotExist if object with case_id doesn't exist
    """

    _validate_cc_list(cc_list)

    TestCase.objects.get(pk=case_id).emailing.remove_cc(cc_list)


@rpc_method(name='TestCase.get_notification_cc')
def get_notification_cc(case_id):
    """
    .. function:: XML-RPC TestCase.get_notification_cc(case_id)

        Return notification list for specified TestCase

        :param case_id: PK of TestCase
        :type case_id: int
        :return: List of email addresses
        :rtype: list(str)
        :raises: TestCase.DoesNotExist if object with case_id doesn't exist
    """
    return TestCase.objects.get(pk=case_id).get_cc_list()


@permissions_required('testcases.add_testcasetag')
@rpc_method(name='TestCase.add_tag')
def add_tag(case_id, tag):
    """
    .. function:: XML-RPC TestCase.add_tag(case_id, tag)

        Add one tag to the specified test case.

        :param case_id: PK of TestCase to modify
        :type case_id: int
        :param tag: Tag name to add
        :type tag: str
        :return: None
        :raises: PermissionDenied if missing *testcases.add_testcasetag* permission
        :raises: TestCase.DoesNotExist if object specified by PK doesn't exist
    """
    tag, _ = Tag.objects.get_or_create(name=tag)
    TestCase.objects.get(pk=case_id).add_tag(tag)


@permissions_required('testcases.delete_testcasetag')
@rpc_method(name='TestCase.remove_tag')
def remove_tag(case_id, tag):
    """
    .. function:: XML-RPC TestCase.remove_tag(case_id, tag)

        Remove tag from a test case.

        :param case_id: PK of TestCase to modify
        :type case_id: int
        :param tag: Tag name to remove
        :type tag: str
        :return: None
        :raises: PermissionDenied if missing *testcases.delete_testcasetag* permission
        :raises: DoesNotExist if objects specified don't exist
    """
    TestCase.objects.get(pk=case_id).remove_tag(
        Tag.objects.get(name=tag)
    )


@permissions_required('testcases.add_testcase')
@rpc_method(name='TestCase.create')
def create(values, **kwargs):
    """
    .. function:: XML-RPC TestCase.create(values)

        Create a new TestCase object and store it in the database.

        :param values: Field values for :class:`tcms.testcases.models.TestCase`
        :type values: dict
        :return: Serialized :class:`tcms.testcases.models.TestCase` object
        :rtype: dict
        :raises: PermissionDenied if missing *testcases.add_testcase* permission

        Minimal test case parameters::

            >>> values = {
                'category': 135,
                'product': 61,
            'summary': 'Testing XML-RPC',
            'priority': 1,
            }
            >>> TestCase.create(values)
    """
    request = kwargs.get(REQUEST_KEY)

    if not (values.get('category') or values.get('summary')):
        raise ValueError()

    if values.get('estimated_time'):
        values['estimated_time'] = parse_duration(values.get('estimated_time'))

    form = NewCaseForm(values)
    form.populate(values.get('product'))

    if form.is_valid():
        # Create the case
        test_case = TestCase.create(author=request.user, values=form.cleaned_data)

        # Add case text to the case
        test_case.add_text(
            action=form.cleaned_data['action'] or '',
            effect=form.cleaned_data['effect'] or '',
            setup=form.cleaned_data['setup'] or '',
            breakdown=form.cleaned_data['breakdown'] or '',
        )

        # Add tag to the case
        for tag in string_to_list(values.get('tag', [])):
            tag, _ = Tag.objects.get_or_create(name=tag)
            test_case.add_tag(tag=tag)
    else:
        # Print the errors if the form is not passed validation.
        raise ValueError(form_errors_to_list(form))

    result = test_case.serialize()
    result['text'] = test_case.latest_text().serialize()

    return result


@rpc_method(name='TestCase.filter')
def filter(query):  # pylint: disable=redefined-builtin
    """
    .. function:: XML-RPC TestCase.filter(query)

        Perform a search and return the resulting list of test cases
        augmented with their latest ``text``.

        :param query: Field lookups for :class:`tcms.testcases.models.TestCase`
        :type query: dict
        :return: Serialized list of :class:`tcms.testcases.models.TestCase` objects.
                 The key ``text`` holds a the latest version of a serialized
                 :class:`tcms.testcases.models.TestCaseText` object!
        :rtype: list(dict)
    """
    if query.get('estimated_time'):
        query['estimated_time'] = parse_duration(query.get('estimated_time'))

    results = []
    for case in TestCase.objects.filter(**query):
        serialized_case = case.serialize()
        serialized_case['text'] = case.latest_text().serialize()
        results.append(serialized_case)

    return results


@permissions_required('testcases.change_testcase')
@rpc_method(name='TestCase.update')
def update(case_id, values, **kwargs):
    """
    .. function:: XML-RPC TestCase.update(case_id, values)

        Update the fields of the selected test case.

        :param case_id: PK of TestCase to be modified
        :type case_id: int
        :param values: Field values for :class:`tcms.testcases.models.TestCase`.
                       The special keys ``setup``, ``breakdown``, ``action`` and
                       ``effect`` are recognized and will cause update of the underlying
                       :class:`tcms.testcases.models.TestCaseText` object!
        :type values: dict
        :return: Serialized :class:`tcms.testcases.models.TestCase` object
        :rtype: dict
        :raises: TestCase.DoesNotExist if object specified by PK doesn't exist
        :raises: PermissionDenied if missing *testcases.change_testcase* permission
    """
    if values.get('estimated_time'):
        values['estimated_time'] = parse_duration(values.get('estimated_time'))

    form = UpdateCaseForm(values)

    if values.get('category') and not values.get('product'):
        raise ValueError('Product ID is required for category')

    if values.get('product'):
        form.populate(product_id=values['product'])

    if form.is_valid():
        test_case = TestCase.objects.get(pk=case_id)
        for key in values.keys():
            # only modify attributes that were passed via parameters
            # skip attributes which are Many-to-Many relations
            if key not in ['component', 'tag'] and hasattr(test_case, key):
                setattr(test_case, key, form.cleaned_data[key])
        test_case.save()

        # if we're updating the text if any one of these parameters was
        # specified
        if any(x in ['setup', 'action', 'effect', 'breakdown'] for x in values.keys()):
            action = form.cleaned_data.get('action', '').strip()
            effect = form.cleaned_data.get('effect', '').strip()
            setup = form.cleaned_data.get('setup', '').strip()
            breakdown = form.cleaned_data.get('breakdown', '').strip()
            author = kwargs.get(REQUEST_KEY).user

            test_case.add_text(
                author=author,
                action=action,
                effect=effect,
                setup=setup,
                breakdown=breakdown,
            )
    else:
        raise ValueError(form_errors_to_list(form))

    return test_case.serialize()
