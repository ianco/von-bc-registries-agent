#!/usr/bin/python

import asyncio
from aiohttp import (
    web,
    ClientSession,
    ClientRequest,
    ClientResponse,
    ClientError,
    ClientTimeout,
)
import json
import os
import threading
import time
from datetime import datetime
import requests
import logging
import random


USE_AIOHTTP = False
CRED_COUNT  = 300
CRED_BATCH  = 32
CRED_PAGE   = 50

AGENT_ADMIN_URL = "http://localhost:8034"

AGENT_ADMIN_API_KEY = os.environ.get("AGENT_ADMIN_API_KEY")
ADMIN_REQUEST_HEADERS = {
    "Content-Type": "application/json",
    "accept": "application/json",
}
if AGENT_ADMIN_API_KEY is not None and 0 < len(AGENT_ADMIN_API_KEY):
    ADMIN_REQUEST_HEADERS["x-api-key"] = AGENT_ADMIN_API_KEY

SCHEMA_TEMPLATE = {
    "schema_name": "registration.registries.ca",
    "schema_version": "1.0.42",
    "attributes": [
        "registration_id","registration_date","registration_expiry_date","registration_renewal_effective","entity_name",
        "entity_name_effective","entity_name_assumed","entity_name_assumed_effective","entity_name_trans","entity_name_trans_effective",
        "entity_status","entity_status_effective","entity_type","registered_jurisdiction","extra_jurisdictional_registration",
        "home_jurisdiction","effective_date","reason_description","expiry_date",
    ],
}

CRED_DEF_TEMPLATE = {
  "support_revocation": False,
  "schema_id": "",
  "tag": "default"
}

CREDENTIAL_ATTR_TEMPLATE = [
    {"name": "registration_id", "value": "value_1"},
    {"name": "registration_date", "value": "value_2"},
    {"name": "registration_expiry_date", "value": "value_3"},
    {"name": "registration_renewal_effective", "value": "value_4"},
    {"name": "entity_name", "value": "value_5"},
    {"name": "entity_name_effective", "value": "value_6"},
    {"name": "entity_name_assumed", "value": "value_7"},
    {"name": "entity_name_assumed_effective", "value": "value_8"},
    {"name": "entity_name_trans", "value": "value_9"},
    {"name": "entity_name_trans_effective", "value": "value_10"},
    {"name": "entity_status", "value": "value_11"},
    {"name": "entity_status_effective", "value": "value_12"},
    {"name": "entity_type", "value": "value_13"},
    {"name": "registered_jurisdiction", "value": "value_14"},
    {"name": "extra_jurisdictional_registration", "value": "value_15"},
    {"name": "home_jurisdiction", "value": "value_16"},
    {"name": "effective_date", "value": "value_17"},
    {"name": "reason_description", "value": "value_18"},
    {"name": "expiry_date", "value": "value_19"},
]


async def agent_schemas_cred_defs(agent_admin_url):
    ret_schemas = {}

    # get loaded cred defs and schemas
    if USE_AIOHTTP:
        client_session: ClientSession = ClientSession()
        async with client_session.request(
            'GET',
            agent_admin_url + "/schemas/created",
        ) as resp:
            resp_status = resp.status
            resp_text = await resp.text()
            await client_session.close()
            if resp_status >= 400:
                raise Exception("Error: " + str(resp_status))
            schemas = json.loads(resp_text)["schema_ids"]
    else:
        response = requests.get(
            agent_admin_url + "/schemas/created",
            headers=ADMIN_REQUEST_HEADERS,
        )
        response.raise_for_status()
        schemas = response.json()["schema_ids"]

    for schema_id in schemas:
        if USE_AIOHTTP:
            client_session: ClientSession = ClientSession()
            async with client_session.request(
                'GET',
                agent_admin_url + "/schemas/" + schema_id,
            ) as resp:
                resp_status = resp.status
                resp_text = await resp.text()
                await client_session.close()
                if resp_status >= 400:
                    raise Exception("Error: " + str(resp_status))
                schema = json.loads(resp_text)["schema"]
        else:
            response = requests.get(
                agent_admin_url + "/schemas/" + schema_id,
                headers=ADMIN_REQUEST_HEADERS,
            )
            response.raise_for_status()
            schema = response.json()["schema"]

        if schema:
            schema_key = schema["name"] + "::" + schema["version"]
            ret_schemas[schema_key] = {
                "schema": schema,
                "schema_id": str(schema["seqNo"])
            }

    if USE_AIOHTTP:
        client_session: ClientSession = ClientSession()
        async with client_session.request(
            'GET',
            agent_admin_url + "/credential-definitions/created",
        ) as resp:
            resp_status = resp.status
            resp_text = await resp.text()
            await client_session.close()
            if resp_status >= 400:
                raise Exception("Error: " + str(resp_status))
            cred_defs = json.loads(resp_text)["credential_definition_ids"]
    else:
        response = requests.get(
            agent_admin_url + "/credential-definitions/created",
            headers=ADMIN_REQUEST_HEADERS,
        )
        response.raise_for_status()
        cred_defs = response.json()["credential_definition_ids"]

    for cred_def_id in cred_defs:
        if USE_AIOHTTP:
            client_session: ClientSession = ClientSession()
            async with client_session.request(
                'GET',
                agent_admin_url + "/credential-definitions/" + cred_def_id,
            ) as resp:
                resp_status = resp.status
                resp_text = await resp.text()
                await client_session.close()
                if resp_status >= 400:
                    raise Exception("Error: " + str(resp_status))
                cred_def = json.loads(resp_text)["credential_definition"]
        else:
            response = requests.get(
                agent_admin_url + "/credential-definitions/" + cred_def_id,
                headers=ADMIN_REQUEST_HEADERS,
            )
            response.raise_for_status()
            cred_def = response.json()["credential_definition"]

        if cred_def:
            for schema_key in ret_schemas:
                if ret_schemas[schema_key]["schema_id"] == cred_def["schemaId"]:
                    ret_schemas[schema_key]["cred_def"] = cred_def
                    break

    return ret_schemas


async def main():
    # get schema information from the agent
    schemas = await agent_schemas_cred_defs(AGENT_ADMIN_URL)
    registration_schema = schemas[SCHEMA_TEMPLATE["schema_name"] + "::" + SCHEMA_TEMPLATE["schema_version"]]
    schema_id = registration_schema["schema"]["id"]
    schema_attrs = registration_schema["schema"]["attrNames"]
    cred_def_id = registration_schema["cred_def"]["id"]

    CRED_DEF_TEMPLATE["schema_id"] = schema_id

    # get the orgbook connection
    if USE_AIOHTTP:
        client_session: ClientSession = ClientSession()
        async with client_session.request(
            'GET',
            AGENT_ADMIN_URL + "/connections?alias=tob-agent",
        ) as resp:
            resp_status = resp.status
            resp_text = await resp.text()
            await client_session.close()
            if resp_status >= 400:
                raise Exception("Error: " + str(resp_status))
            connection = json.loads(resp_text)["results"][0]
    else:
        response = requests.get(
            AGENT_ADMIN_URL + "/connections?alias=tob-agent",
            headers=ADMIN_REQUEST_HEADERS,
        )
        response.raise_for_status()
        connection = response.json()["results"][0]

    issuer_connection_id = connection["connection_id"]

    # now try submitting a bunch of rando credentials
    cred_parts = cred_def_id.split(":")
    issuer_did = cred_parts[0]
    issuer_schema_id = schema_id
    issuer_credential_definition_id = cred_def_id

    cred_count = CRED_COUNT
    cred_batch = CRED_BATCH

    cred_exch_ids_in_flight = []
    cred_exch_ids = []
    j = 0
    issued = 0
    start_time = time.perf_counter()
    print(start_time, "Issuing credentials for:", issuer_credential_definition_id)
    for i in range(1, cred_count+1):
        if 0 == i % CRED_PAGE:
            print("Issued:", i)
        cred_attrs = CREDENTIAL_ATTR_TEMPLATE.copy()
        for ii in range(0, len(cred_attrs)-1):
            cred_attrs[ii]["value"] = cred_attrs[ii]["value"] + "_" + str(random.randint(100000, 999999))
        credential_offer = {
            "schema_issuer_did": issuer_did,
            "issuer_did": issuer_did,
            "schema_name": SCHEMA_TEMPLATE["schema_name"],
            "cred_def_id": issuer_credential_definition_id,
            "schema_version": SCHEMA_TEMPLATE["schema_version"],
            "credential_proposal": {
                "@type": "did:sov:BzCbsNYhMrjHiqZDTUASHg;spec/issue-credential/1.0/credential-preview",
                "attributes": CREDENTIAL_ATTR_TEMPLATE.copy(),
            },
            "connection_id": issuer_connection_id,
            "schema_id": issuer_schema_id,
        }

        # loop this multiple times
        if USE_AIOHTTP:
            client_session: ClientSession = ClientSession()
            async with client_session.request(
                'POST',
                AGENT_ADMIN_URL + "/issue-credential/send",
                json=credential_offer,
            ) as resp:
                resp_status = resp.status
                resp_text = await resp.text()
                await client_session.close()
                if resp_status >= 400:
                    raise Exception("Error: " + str(resp_status))
                resp_json = json.loads(resp_text)
        else:
            response = requests.post(
                AGENT_ADMIN_URL + "/issue-credential/send",
                data=json.dumps(credential_offer),
                headers=ADMIN_REQUEST_HEADERS,
            )
            response.raise_for_status()
            resp_json = response.json()

        issued = i

        # Get the thread ID from the response text.
        cred_exch_ids_in_flight.append(resp_json["credential_exchange_id"])
        cred_exch_ids.append(resp_json["credential_exchange_id"])

        count = 100
        while (cred_batch <= len(cred_exch_ids_in_flight) or (i == cred_count and 0 < len(cred_exch_ids_in_flight))) and 0 < count:
            for cred_exch_id in cred_exch_ids_in_flight.copy():
                if USE_AIOHTTP:
                    client_session: ClientSession = ClientSession()
                    async with client_session.request(
                        'GET',
                        AGENT_ADMIN_URL + "/issue-credential/records/" + cred_exch_id,
                    ) as resp:
                        resp_status = resp.status
                        resp_text = await resp.text()
                        await client_session.close()
                        if resp_status >= 400:
                            raise Exception("Error: " + str(resp_status))
                        resp_json = json.loads(resp_text)
                else:
                    response = requests.get(
                        AGENT_ADMIN_URL + "/issue-credential/records/" + cred_exch_id,
                        headers=ADMIN_REQUEST_HEADERS,
                    )
                    response.raise_for_status()
                    resp_json = response.json()

                cred_exch_state = resp_json["state"]
                if cred_exch_state == "credential_acked":
                    cred_exch_ids_in_flight.remove(cred_exch_id)
                    j = j + 1
                    if 0 == j % CRED_PAGE:
                        print("Acked:", j)

            if cred_batch <= len(cred_exch_ids_in_flight):
                time.sleep(0.1)

            count = count - 1

        if count == 0:
            print("timeout!")

    processing_time = time.perf_counter() - start_time
    print("Issued:", issued, ", Acked:", j)
    print("Processing time:", processing_time, (60*issued/processing_time), "CPM")


if __name__ == "__main__":
    try:
        asyncio.get_event_loop().run_until_complete(
            main()
        )
    except KeyboardInterrupt:
        os._exit(1)
