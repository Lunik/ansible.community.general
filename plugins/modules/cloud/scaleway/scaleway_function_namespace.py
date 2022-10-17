#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# Scaleway Serverless function namespace management module
#
# Copyright (c) 2022, Guillaume MARTINEZ <lunik@tiwabbit.fr>
# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt or https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = '''
---
module: scaleway_function_namespace
short_description: Scaleway Function namespace management module
version_added: 5.8.0
author: Guillaume MARTINEZ (@Lunik)
description:
  - This module manages function namespaces on Scaleway account.
extends_documentation_fragment:
  - community.general.scaleway
  - community.general.scaleway_waitable_resource


options:
  state:
    type: str
    description:
      - Indicate desired state of the function namespace.
    default: present
    choices:
      - present
      - absent

  project_id:
    type: str
    description:
      - Project identifier.
    required: true

  region:
    type: str
    description:
      - Scaleway region to use (for example C(fr-par)).
    required: true
    choices:
      - fr-par
      - nl-ams
      - pl-waw

  name:
    type: str
    description:
      - Name of the function namespace.
    required: true

  description:
    description:
      - Description of the function namespace.
    type: str

  environment_variables:
    description:
      - Environment variables of the function namespace.
      - Injected in functions at runtime.
    type: dict

  secret_environment_variables:
    description:
      - Secret environment variables of the function namespace.
      - Updating thoses values will not output a C(changed) state in Ansible.
      - Injected in functions at runtime.
    type: dict
'''

EXAMPLES = '''
- name: Create a function namespace
  community.general.scaleway_function_namespace:
    project_id: '{{ scw_project }}'
    state: present
    region: fr-par
    name: my-awesome-function-namespace
    environment_variables:
      MY_VAR: my_value
    secret_environment_variables:
      MY_SECRET_VAR: my_secret_value
  register: function_namespace_creation_task

- name: Make sure function namespace is deleted
  community.general.scaleway_function_namespace:
    project_id: '{{ scw_project }}'
    state: absent
    region: fr-par
    name: my-awesome-function-namespace
'''

RETURN = '''
function_namespace:
    description: The function namespace informations.
    returned: when I(state=present)
    type: dict
    sample: {
      "description": "",
      "environment_variables": {
          "MY_VAR": "my_value"
      },
      "error_message": null,
      "id": "531a1fd7-98d2-4a74-ad77-d398324304b8",
      "name": "my-awesome-function-namespace",
      "organization_id": "e04e3bdc-015c-4514-afde-9389e9be24b0",
      "project_id": "d44cea58-dcb7-4c95-bff1-1105acb60a98",
      "region": "fr-par",
      "registry_endpoint": "",
      "registry_namespace_id": "",
      "secret_environment_variables": "SENSITIVE_VALUE",
      "status": "pending"
    }
'''

from ansible_collections.community.general.plugins.module_utils.scaleway import (
    SCALEWAY_ENDPOINT, SCALEWAY_REGIONS, scaleway_argument_spec, Scaleway,
    wait_to_complete_state_transition, scaleway_waitable_resource_argument_spec,
    filter_sensitive_attributes, resource_attributes_should_be_changed,
    fetch_all_resources
)
from ansible.module_utils.basic import AnsibleModule

STABLE_STATES = (
    "ready",
    "absent"
)

VERIFIABLE_MUTABLE_ATTRIBUTES = (
    "description",
    "environment_variables"
)

MUTABLE_ATTRIBUTES = VERIFIABLE_MUTABLE_ATTRIBUTES + (
    "secret_environment_variables",
)

SENSITIVE_ATTRIBUTES = (
    "secret_environment_variables",
)


def payload_from_wished_fn(wished_fn):
    playload = {
        "project_id": wished_fn["project_id"],
        "name": wished_fn["name"],
        "description": wished_fn["description"],
        "environment_variables": wished_fn["environment_variables"],
        "secret_environment_variables": [
            dict(key=var[0], value=var[1])
            for var in wished_fn["secret_environment_variables"].items()
        ]
    }

    return playload


def absent_strategy(api, wished_fn):
    changed = False

    fn_list = fetch_all_resources(api, "namespaces")
    fn_lookup = dict((fn["name"], fn)
                     for fn in fn_list)

    if wished_fn["name"] not in fn_lookup.keys():
        return changed, {}

    target_fn = fn_lookup[wished_fn["name"]]
    changed = True
    if api.module.check_mode:
        return changed, {"status": "Function namespace would be destroyed"}

    wait_to_complete_state_transition(api=api, resource=target_fn, stable_states=STABLE_STATES, force_wait=True)
    response = api.delete(path=api.api_path + "/%s" % target_fn["id"])
    if not response.ok:
        api.module.fail_json(msg='Error deleting function namespace [{0}: {1}]'.format(
            response.status_code, response.json))

    wait_to_complete_state_transition(api=api, resource=target_fn, stable_states=STABLE_STATES)
    return changed, response.json


def present_strategy(api, wished_fn):
    changed = False

    fn_list = fetch_all_resources(api, "namespaces")
    fn_lookup = dict((fn["name"], fn)
                     for fn in fn_list)

    playload_fn = payload_from_wished_fn(wished_fn)

    if wished_fn["name"] not in fn_lookup.keys():
        changed = True
        if api.module.check_mode:
            return changed, {"status": "A function namespace would be created."}

        # Create function namespace
        api.warn(playload_fn)
        creation_response = api.post(path=api.api_path,
                                     data=playload_fn)

        if not creation_response.ok:
            msg = "Error during function namespace creation: %s: '%s' (%s)" % (creation_response.info['msg'],
                                                                               creation_response.json['message'],
                                                                               creation_response.json)
            api.module.fail_json(msg=msg)

        wait_to_complete_state_transition(api=api, resource=creation_response.json, stable_states=STABLE_STATES)
        response = api.get(path=api.api_path + "/%s" % creation_response.json["id"])
        return changed, response.json

    target_fn = fn_lookup[wished_fn["name"]]
    patch_payload = resource_attributes_should_be_changed(target=target_fn,
                                                          wished=playload_fn,
                                                          verifiable_mutable_attributes=VERIFIABLE_MUTABLE_ATTRIBUTES,
                                                          mutable_attributes=MUTABLE_ATTRIBUTES)

    if not patch_payload:
        return changed, target_fn

    changed = True
    if api.module.check_mode:
        return changed, {"status": "Function namespace attributes would be changed."}

    fn_patch_response = api.patch(path=api.api_path + "/%s" % target_fn["id"],
                                  data=patch_payload)

    if not fn_patch_response.ok:
        api.module.fail_json(msg='Error during function namespace attributes update: [{0}: {1}]'.format(
            fn_patch_response.status_code, fn_patch_response.json['message']))

    wait_to_complete_state_transition(api=api, resource=target_fn, stable_states=STABLE_STATES)
    response = api.get(path=api.api_path + "/%s" % target_fn["id"])
    return changed, response.json


state_strategy = {
    "present": present_strategy,
    "absent": absent_strategy
}


def core(module):
    region = module.params["region"]
    wished_function_namespace = {
        "state": module.params["state"],
        "project_id": module.params["project_id"],
        "name": module.params["name"],
        "description": module.params['description'],
        "environment_variables": module.params['environment_variables'],
        "secret_environment_variables": module.params['secret_environment_variables']
    }

    api = Scaleway(module=module)
    api.api_path = "functions/v1beta1/regions/%s/namespaces" % region

    changed, summary = state_strategy[wished_function_namespace["state"]](api=api, wished_fn=wished_function_namespace)

    module.exit_json(changed=changed, function_namespace=filter_sensitive_attributes(summary, SENSITIVE_ATTRIBUTES))


def main():
    argument_spec = scaleway_argument_spec()
    argument_spec.update(scaleway_waitable_resource_argument_spec())
    argument_spec.update(dict(
        state=dict(type='str', default='present', choices=['absent', 'present']),
        project_id=dict(type='str', required=True),
        region=dict(type='str', required=True, choices=SCALEWAY_REGIONS),
        name=dict(type='str', required=True),
        description=dict(type='str', default=''),
        environment_variables=dict(type='dict', default={}),
        secret_environment_variables=dict(type='dict', default={}, no_log=True)
    ))
    module = AnsibleModule(
        argument_spec=argument_spec,
        supports_check_mode=True,
    )

    core(module)


if __name__ == '__main__':
    main()
