import copy

from crispy_forms.bootstrap import TabHolder
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Column
from django import forms
from django.contrib.auth.admin import csrf_protect_m
from django.db import transaction
from django.http import HttpResponseRedirect
from django.template.response import TemplateResponse
from django.utils.translation import ugettext as _

from xadmin.layout import Container, Col, Fieldset
from xadmin.views import filter_hook
from xadmin.views.base import CommAdminView


class FormAdminView(CommAdminView):
    form = forms.ModelForm
    title = None
    readonly_fields = ()

    form_template = 'xadmin/views/form.html'

    form_layout = None

    def init_request(self, *args, **kwargs):
        # comm method for both get and post
        self.prepare_form()

    @filter_hook
    def prepare_form(self):
        self.view_form = self.form

    @filter_hook
    def instance_forms(self):
        self.form_obj = self.view_form(**self.get_form_datas())

    def setup_forms(self):
        helper = self.get_form_helper()
        if helper:
            self.form_obj.helper = helper

    @filter_hook
    def valid_forms(self):
        return self.form_obj.is_valid()

    @filter_hook
    def get_form_layout(self):
        layout = copy.deepcopy(self.form_layout)
        fields = self.form_obj.fields.keys()

        if layout is None:
            layout = Layout(
                Container(
                    Col(
                        'full',
                        Fieldset('', *fields, css_class="unsort no_title"),
                        horizontal=True,
                        span=12
                    )
                )
            )
        elif type(layout) in (list, tuple) and len(layout) > 0:
            if isinstance(layout[0], Column):
                fs = layout
            elif isinstance(layout[0], (Fieldset, TabHolder)):
                fs = (Col('full', *layout, horizontal=True, span=12),)
            else:
                fs = (Col('full', Fieldset('', *layout, css_class='unsort no_title'), horizontal=True, span=12),)

            layout = Layout(Container(*fs))

            rendered_fields = [i[1] for i in layout.get_field_names()]
            container = layout[0].fields
            other_fieldset = Fieldset(_('Other Fields'), *[f for f in fields if f not in rendered_fields])

            if len(other_fieldset.fields):
                if len(container) and isinstance(container[0], Column):
                    container[0].fields.append(other_fieldset)
                else:
                    container.append(other_fieldset)

        return layout

    @filter_hook
    def get_form_helper(self):
        helper = FormHelper()
        helper.form_tag = False
        helper.include_media = False
        helper.add_layout(self.get_form_layout())

        return helper

    @filter_hook
    def save_forms(self):
        pass

    @csrf_protect_m
    @filter_hook
    def get(self, request, *args, **kwargs):
        self.instance_forms()
        self.setup_forms()

        return self.get_response()

    @csrf_protect_m
    @transaction.atomic
    @filter_hook
    def post(self, request, *args, **kwargs):
        self.instance_forms()
        self.setup_forms()

        if self.valid_forms():
            self.save_forms()
            response = self.post_response()
            if isinstance(response, str):
                return HttpResponseRedirect(response)
            else:
                return response

        return self.get_response()

    @filter_hook
    def get_context(self):
        context = super(FormAdminView, self).get_context()
        context.update({
            'form': self.form_obj,
            'title': self.title,
        })
        return context

    @filter_hook
    def get_media(self):
        return super(FormAdminView, self).get_media() + self.form_obj.media + \
               self.vendor('xadmin.page.form.js', 'xadmin.form.css')

    def get_initial_data(self):
        return {}

    @filter_hook
    def get_form_datas(self):
        data = {'initial': self.get_initial_data()}
        if self.request_method == 'get':
            data['initial'].update(self.request.GET)
        else:
            data.update({'data': self.request.POST, 'files': self.request.FILES})
        return data

    @filter_hook
    def get_breadcrumb(self):
        bcs = super(FormAdminView, self).get_breadcrumb()
        bcs.append({'title': self.title})
        return bcs

    @filter_hook
    def get_response(self):
        context = self.get_context()
        context.update(self.kwargs or {})

        return TemplateResponse(
            self.request, self.form_template,
            context)

    @filter_hook
    def post_response(self):
        request = self.request

        msg = _('The %s was changed successfully.') % self.title
        self.message_user(msg, 'success')

        if "_redirect" in request.GET:
            return request.GET["_redirect"]
        else:
            return self.get_redirect_url()

    @filter_hook
    def get_redirect_url(self):
        return self.get_admin_url('index')
