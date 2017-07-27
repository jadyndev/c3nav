import typing
from contextlib import suppress

from django.contrib import messages
from django.core.exceptions import FieldDoesNotExist, ObjectDoesNotExist
from django.db import models
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.translation import ugettext_lazy as _

from c3nav.editor.forms import (GraphEdgeSettingsForm, GraphEditorActionForm, GraphEditorSettingsForm,
                                GraphNodeSettingsForm)
from c3nav.editor.views.base import sidebar_view


def child_model(request, model: typing.Union[str, models.Model], kwargs=None, parent=None):
    model = request.changeset.wrap_model(model)
    related_name = model._meta.default_related_name
    if parent is not None:
        qs = getattr(parent, related_name)
        if hasattr(model, 'q_for_request'):
            qs = qs.filter(model.q_for_request(request))
        count = qs.count()
    else:
        count = None
    return {
        'title': model._meta.verbose_name_plural,
        'url': reverse('editor.'+related_name+'.list', kwargs=kwargs),
        'count': count,
    }


@sidebar_view
def main_index(request):
    Level = request.changeset.wrap_model('Level')
    return render(request, 'editor/index.html', {
        'levels': Level.objects.filter(Level.q_for_request(request), on_top_of__isnull=True),
        'can_edit': request.changeset.can_edit(request),
        'child_models': [
            child_model(request, 'LocationGroupCategory'),
            child_model(request, 'LocationGroup'),
            child_model(request, 'AccessRestriction'),
            child_model(request, 'Source'),
        ],
    })


@sidebar_view
def level_detail(request, pk):
    Level = request.changeset.wrap_model('Level')
    qs = Level.objects.filter(Level.q_for_request(request))
    level = get_object_or_404(qs.select_related('on_top_of').prefetch_related('levels_on_top'), pk=pk)

    return render(request, 'editor/level.html', {
        'levels': Level.objects.filter(Level.q_for_request(request), on_top_of__isnull=True),
        'level': level,
        'level_url': 'editor.levels.detail',
        'level_as_pk': True,
        'can_edit': request.changeset.can_edit(request),

        'child_models': [child_model(request, model_name, kwargs={'level': pk}, parent=level)
                         for model_name in ('Building', 'Space', 'Door')],
        'levels_on_top': level.levels_on_top.filter(Level.q_for_request(request)).all(),
        'geometry_url': '/api/editor/geometries/?level='+str(level.primary_level_pk),
    })


@sidebar_view
def space_detail(request, level, pk):
    Space = request.changeset.wrap_model('Space')
    qs = Space.objects.filter(Space.q_for_request(request))
    space = get_object_or_404(qs.select_related('level'), level__pk=level, pk=pk)

    return render(request, 'editor/space.html', {
        'level': space.level,
        'space': space,
        'can_edit': request.changeset.can_edit(request),

        'child_models': [child_model(request, model_name, kwargs={'space': pk}, parent=space)
                         for model_name in ('Hole', 'Area', 'Stair', 'Obstacle', 'LineObstacle', 'Column', 'POI')],
        'geometry_url': '/api/editor/geometries/?space='+pk,
    })


@sidebar_view
def edit(request, pk=None, model=None, level=None, space=None, on_top_of=None, explicit_edit=False):
    model = request.changeset.wrap_model(model)
    related_name = model._meta.default_related_name

    Level = request.changeset.wrap_model('Level')
    Space = request.changeset.wrap_model('Space')

    can_edit = request.changeset.can_edit(request)

    obj = None
    if pk is not None:
        # Edit existing map item
        kwargs = {'pk': pk}
        qs = model.objects.all()
        if hasattr(model, 'q_for_request'):
            qs = qs.filter(model.q_for_request(request))
        if level is not None:
            kwargs.update({'level__pk': level})
            qs = qs.select_related('level')
        elif space is not None:
            kwargs.update({'space__pk': space})
            qs = qs.select_related('space')
        obj = get_object_or_404(qs, **kwargs)
    elif level is not None:
        level = get_object_or_404(Level.objects.filter(Level.q_for_request(request)), pk=level)
    elif space is not None:
        space = get_object_or_404(Space.objects.filter(Space.q_for_request(request)), pk=space)
    elif on_top_of is not None:
        on_top_of = get_object_or_404(Level.objects.filter(Level.q_for_request(request), on_top_of__isnull=True),
                                      pk=on_top_of)

    new = obj is None
    # noinspection PyProtectedMember
    ctx = {
        'path': request.path,
        'pk': pk,
        'model_name': model.__name__.lower(),
        'model_title': model._meta.verbose_name,
        'can_edit': can_edit,
        'new': new,
        'title': obj.title if obj else None,
    }

    with suppress(FieldDoesNotExist):
        ctx.update({
            'geomtype': model._meta.get_field('geometry').geomtype,
        })

    if model == Level:
        ctx.update({
            'level': obj,
            'back_url': reverse('editor.index') if new else reverse('editor.levels.detail', kwargs={'pk': pk}),
            'nozoom': True,
        })
        if not new:
            ctx.update({
                'geometry_url': '/api/editor/geometries/?level='+str(obj.primary_level_pk),
                'on_top_of': obj.on_top_of,
            })
        elif on_top_of:
            ctx.update({
                'geometry_url': '/api/editor/geometries/?level=' + str(on_top_of.pk),
                'on_top_of': on_top_of,
                'back_url': reverse('editor.levels.detail', kwargs={'pk': on_top_of.pk}),
            })
    elif model == Space and not new:
        level = obj.level
        ctx.update({
            'level': obj.level,
            'back_url': reverse('editor.spaces.detail', kwargs={'level': obj.level.pk, 'pk': pk}),
            'geometry_url': '/api/editor/geometries/?space='+pk,
            'nozoom': True,
        })
    elif model == Space and new:
        ctx.update({
            'level': level,
            'back_url': reverse('editor.spaces.list', kwargs={'level': level.pk}),
            'geometry_url': '/api/editor/geometries/?level='+str(level.primary_level_pk),
            'nozoom': True,
        })
    elif hasattr(model, 'level'):
        if not new:
            level = obj.level
        ctx.update({
            'level': level,
            'back_url': reverse('editor.'+related_name+'.list', kwargs={'level': level.pk}),
            'geometry_url': '/api/editor/geometries/?level='+str(level.primary_level_pk),
        })
    elif hasattr(model, 'space'):
        if not new:
            space = obj.space
        ctx.update({
            'level': space.level,
            'back_url': reverse('editor.'+related_name+'.list', kwargs={'space': space.pk}),
            'geometry_url': '/api/editor/geometries/?space='+str(space.pk),
        })
    else:
        kwargs = {}
        if level is not None:
            kwargs.update({'level': level})
        elif space is not None:
            kwargs.update({'space': space})

        ctx.update({
            'back_url': reverse('.'.join(request.resolver_match.url_name.split('.')[:-1]+['list']), kwargs=kwargs),
        })

    if request.method == 'POST':
        if not new and request.POST.get('delete') == '1':
            # Delete this mapitem!
            try:
                if not request.changeset.get_changed_object(obj).can_delete():
                    raise PermissionError
            except (ObjectDoesNotExist, PermissionError):
                messages.error(request, _('You can not delete this object because other objects still depend on it.'))
                return redirect(request.path)

            if request.POST.get('delete_confirm') == '1':
                with request.changeset.lock_to_edit(request) as changeset:
                    if changeset.can_edit(request):
                        obj.delete()
                    else:
                        messages.error(request, _('You can not edit changes on this changeset.'))
                        return redirect(request.path)
                messages.success(request, _('Object was successfully deleted.'))
                if model == Level:
                    if obj.on_top_of_id is not None:
                        return redirect(reverse('editor.levels.detail', kwargs={'pk': obj.on_top_of_id}))
                    return redirect(reverse('editor.index'))
                elif model == Space:
                    return redirect(reverse('editor.spaces.list', kwargs={'level': obj.level.pk}))
                return redirect(ctx['back_url'])
            ctx['obj_title'] = obj.title
            return render(request, 'editor/delete.html', ctx)

        form = model.EditorForm(instance=model() if new else obj, data=request.POST, request=request)
        if form.is_valid():
            # Update/create objects
            obj = form.save(commit=False)

            if form.titles is not None:
                obj.titles = {}
                for language, title in form.titles.items():
                    if title:
                        obj.titles[language] = title

            if level is not None:
                obj.level = level

            if space is not None:
                obj.space = space

            if on_top_of is not None:
                obj.on_top_of = on_top_of

            with request.changeset.lock_to_edit(request) as changeset:
                if changeset.can_edit(request):
                    obj.save()

                    if form.redirect_slugs is not None:
                        for slug in form.add_redirect_slugs:
                            obj.redirects.create(slug=slug)

                        for slug in form.remove_redirect_slugs:
                            obj.redirects.filter(slug=slug).delete()

                    form.save_m2m()
                    messages.success(request, _('Object was successfully saved.'))
                    return redirect(ctx['back_url'])
                else:
                    messages.error(request, _('You can not edit changes on this changeset.'))

    else:
        form = model.EditorForm(instance=obj, request=request)

    ctx.update({
        'form': form,
    })

    return render(request, 'editor/edit.html', ctx)


@sidebar_view
def list_objects(request, model=None, level=None, space=None, explicit_edit=False):
    if not request.resolver_match.url_name.endswith('.list'):
        raise ValueError('url_name does not end with .list')

    model = request.changeset.wrap_model(model)

    Level = request.changeset.wrap_model('Level')
    Space = request.changeset.wrap_model('Space')

    can_edit = request.changeset.can_edit(request)

    ctx = {
        'path': request.path,
        'model_name': model.__name__.lower(),
        'model_title': model._meta.verbose_name,
        'model_title_plural': model._meta.verbose_name_plural,
        'explicit_edit': explicit_edit,
        'can_edit': can_edit,
    }

    queryset = model.objects.all().order_by('id')
    if hasattr(model, 'q_for_request'):
        queryset = queryset.filter(model.q_for_request(request))
    reverse_kwargs = {}

    if level is not None:
        reverse_kwargs['level'] = level
        level = get_object_or_404(Level.objects.filter(Level.q_for_request(request)), pk=level)
        queryset = queryset.filter(level=level).defer('geometry')
        ctx.update({
            'back_url': reverse('editor.levels.detail', kwargs={'pk': level.pk}),
            'back_title': _('back to level'),
            'levels': Level.objects.filter(Level.q_for_request(request), on_top_of__isnull=True),
            'level': level,
            'level_url': request.resolver_match.url_name,
            'geometry_url': '/api/editor/geometries/?level='+str(level.primary_level_pk),
        })
    elif space is not None:
        reverse_kwargs['space'] = space
        sub_qs = Space.objects.filter(Space.q_for_request(request)).select_related('level').defer('geometry')
        space = get_object_or_404(sub_qs, pk=space)
        queryset = queryset.filter(space=space).defer('geometry')
        ctx.update({
            'level': space.level,
            'back_url': reverse('editor.spaces.detail', kwargs={'level': space.level.pk, 'pk': space.pk}),
            'back_title': _('back to space'),
            'geometry_url': '/api/editor/geometries/?space='+str(space.pk),
        })
    else:
        ctx.update({
            'back_url': reverse('editor.index'),
            'back_title': _('back to overview'),
        })

    edit_url_name = request.resolver_match.url_name[:-4]+('detail' if explicit_edit else 'edit')
    for obj in queryset:
        reverse_kwargs['pk'] = obj.pk
        obj.edit_url = reverse(edit_url_name, kwargs=reverse_kwargs)
    reverse_kwargs.pop('pk', None)

    ctx.update({
        'create_url': reverse(request.resolver_match.url_name[:-4] + 'create', kwargs=reverse_kwargs),
        'objects': queryset,
    })

    return render(request, 'editor/list.html', ctx)


def connect_nodes(request, active_node, clicked_node, edge_settings_form, graph_editing_settings):
    connect_nodes_setting = graph_editing_settings['connect_nodes']
    create_existing_edge_setting = graph_editing_settings['create_existing_edge']
    after_connect_nodes_setting = graph_editing_settings['after_connect_nodes']

    new_connections = []
    if connect_nodes_setting in ('bidirectional', 'unidirectional', 'unidirectional_force'):
        new_connections.append((active_node, clicked_node, False))
        if connect_nodes_setting == 'bidirectional':
            new_connections.append((clicked_node, active_node, True))

    if new_connections:
        instance = edge_settings_form.instance
        for from_node, to_node, is_reverse in new_connections:
            existing = from_node.edges_from_here.filter(to_node=to_node).first()
            if existing is None:
                instance.pk = None
                instance.from_node = from_node
                instance.to_node = to_node
                instance.save()
                messages.success(request, _('Reverse edge created.') if is_reverse else _('Edge created.'))
            elif create_existing_edge_setting == 'delete':
                existing.delete()
                messages.success(request, _('Reverse edge deleted.') if is_reverse else _('Edge deleted.'))
            elif create_existing_edge_setting == 'overwrite_toggle':
                if existing.waytype == instance.waytype and existing.access_restriction == instance.access_restriction:
                    existing.delete()
                    messages.success(request, _('Reverse edge deleted.') if is_reverse else _('Edge deleted.'))
                else:
                    existing.waytype = instance.waytype
                    existing.access_restriction = instance.access_restriction
                    existing.save()
                    messages.success(request, _('Reverse edge overwritten.') if is_reverse else _('Edge overwritten.'))
            elif create_existing_edge_setting in ('overwrite_always', 'overwrite_waytype', 'overwrite_access'):
                if create_existing_edge_setting in ('overwrite_always', 'overwrite_waytype'):
                    existing.waytype = instance.waytype
                if create_existing_edge_setting in ('overwrite_always', 'overwrite_access'):
                    existing.access_restriction = instance.access_restriction
                existing.save()
                messages.success(request, _('Reverse edge overwritten.') if is_reverse else _('Edge overwritten.'))

    if connect_nodes_setting in ('delete_unidirectional', 'delete_bidirectional'):
        existing = active_node.edges_from_here.filter(to_node=clicked_node).first()
        if existing is not None:
            existing.delete()
            messages.success(request, _('Edge deleted.'))

    if connect_nodes_setting in ('unidirectional_force', 'delete_bidirectional'):
        existing = clicked_node.edges_from_here.filter(to_node=active_node).first()
        if existing is not None:
            existing.delete()
            messages.success(request, _('Reverse edge deleted.'))

    if after_connect_nodes_setting == 'reset':
        return None, True
    elif after_connect_nodes_setting == 'set_second_active':
        return clicked_node, True
    return active_node, False


@sidebar_view
def graph_edit(request, level=None, space=None):
    Level = request.changeset.wrap_model('Level')
    Space = request.changeset.wrap_model('Space')
    GraphNode = request.changeset.wrap_model('GraphNode')
    GraphEdge = request.changeset.wrap_model('GraphEdge')

    can_edit = request.changeset.can_edit(request)

    ctx = {
        'path': request.path,
        'can_edit': can_edit,
    }

    graph_editing_settings = {field.name: field.initial for field in GraphEditorSettingsForm()}
    graph_editing_settings.update(request.session.get('graph_editing_settings', {}))

    graph_editing = 'edit-nodes'
    allow_clicked_position = False

    if level is not None:
        level = get_object_or_404(Level.objects.filter(Level.q_for_request(request)), pk=level)
        ctx.update({
            'back_url': reverse('editor.levels.detail', kwargs={'pk': level.pk}),
            'back_title': _('back to level'),
            'levels': Level.objects.filter(Level.q_for_request(request), on_top_of__isnull=True),
            'level': level,
            'level_url': request.resolver_match.url_name,
            'geometry_url': '/api/editor/geometries/?level='+str(level.primary_level_pk),
        })
    elif space is not None:
        queryset = Space.objects.filter(Space.q_for_request(request)).select_related('level').defer('geometry')
        space = get_object_or_404(queryset, pk=space)
        ctx.update({
            'space': space,
            'level': space.level,
            'back_url': reverse('editor.spaces.detail', kwargs={'level': space.level.pk, 'pk': space.pk}),
            'back_title': _('back to space'),
            'parent_url': reverse('editor.levels.graph', kwargs={'level': space.level.pk}),
            'parent_title': _('to level graph'),
            'geometry_url': '/api/editor/geometries/?space='+str(space.pk),
        })
        if graph_editing_settings['click_anywhere'] != 'noop':
            graph_editing = 'edit-create-nodes'
            if graph_editing_settings['click_anywhere'] == 'create_node_if_none_active':
                graph_editing = 'edit-create-if-no-active-node'
            elif graph_editing_settings['click_anywhere'] == 'create_node_if_other_active':
                graph_editing = 'edit-create-if-active-node'
            allow_clicked_position = True

    if request.method == 'POST':
        node_settings_form = GraphNodeSettingsForm(instance=GraphNode(), data=request.POST)
        edge_settings_form = GraphEdgeSettingsForm(instance=GraphEdge(), request=request, data=request.POST)
        graph_action_form = GraphEditorActionForm(request=request, allow_clicked_position=allow_clicked_position,
                                                  data=request.POST)
        if node_settings_form.is_valid() and edge_settings_form.is_valid() and graph_action_form.is_valid():
            goto_space = graph_action_form.cleaned_data['goto_space']
            if goto_space is not None:
                return redirect(reverse('editor.spaces.graph', kwargs={'space': goto_space.pk}))

            set_active_node = False
            active_node = graph_action_form.cleaned_data['active_node']
            clicked_node = graph_action_form.cleaned_data['clicked_node']
            clicked_position = graph_action_form.cleaned_data.get('clicked_position')
            if clicked_node is not None and clicked_position is None:
                node_click_setting = graph_editing_settings['node_click']
                if node_click_setting in ('connect', 'connect_or_toggle'):
                    connect = False
                    if node_click_setting == 'connect':
                        connect = True
                    elif active_node is None:
                        active_node = clicked_node
                        set_active_node = True
                    elif active_node == clicked_node:
                        active_node = None
                        set_active_node = True
                    else:
                        connect = True

                    if connect:
                        with request.changeset.lock_to_edit(request) as changeset:
                            if changeset.can_edit(request):
                                active_node, set_active_node = connect_nodes(request, active_node, clicked_node,
                                                                             edge_settings_form, graph_editing_settings)
                            else:
                                messages.error(request, _('You can not edit changes on this changeset.'))
                elif node_click_setting == 'activate':
                    active_node = clicked_node
                    set_active_node = True
                elif node_click_setting == 'deactivate':
                    active_node = None
                    set_active_node = True
                elif node_click_setting == 'toggle':
                    active_node = None if active_node == clicked_node else clicked_node
                    set_active_node = True
                elif node_click_setting == 'set_space_transfer':
                    with request.changeset.lock_to_edit(request) as changeset:
                        if changeset.can_edit(request):
                            clicked_node.space_transfer = node_settings_form.instance.space_transfer
                            clicked_node.save()
                            messages.success(request, _('Space transfer set.'))
                        else:
                            messages.error(request, _('You can not edit changes on this changeset.'))
                elif node_click_setting == 'delete':
                    with request.changeset.lock_to_edit(request) as changeset:
                        if changeset.can_edit(request):
                            try:
                                if not request.changeset.get_changed_object(clicked_node).can_delete():
                                    raise PermissionError
                            except (ObjectDoesNotExist, PermissionError):
                                messages.error(request, _('This node is connected to other nodes.'))
                            else:
                                clicked_node.delete()
                                if clicked_node == active_node:
                                    active_node = None
                                    set_active_node = True
                                messages.success(request, _('Node deleted.'))
                        else:
                            messages.error(request, _('You can not edit changes on this changeset.'))

            elif clicked_node is None and clicked_position is not None:
                click_anywhere_setting = graph_editing_settings['click_anywhere']
                if (click_anywhere_setting == 'create_node' or
                        (click_anywhere_setting != 'create_node_if_none_active' or active_node is None) or
                        (click_anywhere_setting != 'create_node_if_other_active' or active_node is not None)):
                    if space.geometry.contains(clicked_position):
                        with request.changeset.lock_to_edit(request) as changeset:
                            if changeset.can_edit(request):
                                node = node_settings_form.instance
                                node.space = space
                                node.geometry = clicked_position
                                node.save()
                                messages.success(request, _('New graph node created.'))
                                after_create_node_setting = graph_editing_settings['after_create_node']
                                if after_create_node_setting == 'connect':
                                    active_node, set_active_node = connect_nodes(request, active_node, node,
                                                                                 edge_settings_form,
                                                                                 graph_editing_settings)
                                elif after_create_node_setting == 'activate':
                                    active_node = node
                                    set_active_node = True
                                elif after_create_node_setting == 'deactivate':
                                    active_node = None
                                    set_active_node = True
                            else:
                                messages.error(request, _('You can not edit changes on this changeset.'))

            if set_active_node:
                ctx.update({
                    'set_active_node': set_active_node,
                    'active_node': active_node,
                })
    else:
        node_settings_form = GraphNodeSettingsForm()
        edge_settings_form = GraphEdgeSettingsForm(request=request)
    graph_action_form = GraphEditorActionForm(request=request, allow_clicked_position=allow_clicked_position)

    ctx.update({
        'node_settings_form': node_settings_form,
        'edge_settings_form': edge_settings_form,
        'graph_action_form': graph_action_form,
        'graph_editing': graph_editing,
        'deactivate_node_on_click': graph_editing_settings['node_click'] in ('deactivate', 'toggle',
                                                                             'connect_or_toggle'),
    })

    return render(request, 'editor/graph.html', ctx)


@sidebar_view
def graph_editing_settings_view(request):
    ctx: dict = {
        'closemodal': False,
    }
    if request.method == 'POST':
        form = GraphEditorSettingsForm(data=request.POST)
        if form.is_valid():
            messages.success(request, _('Graph Editing Settings were successfully saved.'))
            request.session['graph_editing_settings'] = form.cleaned_data
            if request.POST.get('can_close_modal') == '1':
                ctx['closemodal'] = True
    else:
        graph_editing_settings = {field.name: field.initial for field in GraphEditorSettingsForm()}
        graph_editing_settings.update(request.session.get('graph_editing_settings', {}))
        form = GraphEditorSettingsForm(data=graph_editing_settings)

    ctx.update({
        'form': form,
    })
    return render(request, 'editor/graph_editing_settings.html', ctx)
