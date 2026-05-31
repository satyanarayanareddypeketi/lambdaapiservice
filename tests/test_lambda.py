import json
import os
import boto3
import pytest
from moto import mock_aws

os.environ["DYNAMODB_TABLE"] = "tasks-test"
os.environ["AWS_DEFAULT_REGION"] = "us-east-1"
os.environ["AWS_ACCESS_KEY_ID"] = "testing"
os.environ["AWS_SECRET_ACCESS_KEY"] = "testing"

import myfirstlambdaapi


@pytest.fixture
def table():
    with mock_aws():
        dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
        dynamodb.create_table(
            TableName="tasks-test",
            KeySchema=[{"AttributeName": "task_id", "KeyType": "HASH"}],
            AttributeDefinitions=[{"AttributeName": "task_id", "AttributeType": "S"}],
            BillingMode="PAY_PER_REQUEST",
        )
        yield


def make_event(method, path, body=None, task_id=None):
    return {
        "httpMethod": method,
        "path": path,
        "pathParameters": {"task_id": task_id} if task_id else None,
        "body": json.dumps(body) if body else None,
    }


# ── Health ────────────────────────────────────────────────────────────────────

def test_health_check():
    event = make_event("GET", "/health")
    res = myfirstlambdaapi.lambda_handler(event, None)
    assert res["statusCode"] == 200


# ── Create ────────────────────────────────────────────────────────────────────

def test_create_task(table):
    event = make_event("POST", "/tasks", body={"title": "Fix bug", "description": "Login broken"})
    res = myfirstlambdaapi.lambda_handler(event, None)
    assert res["statusCode"] == 201
    body = json.loads(res["body"])
    assert body["title"] == "Fix bug"
    assert body["status"] == "PENDING"
    assert "task_id" in body


def test_create_task_missing_fields(table):
    event = make_event("POST", "/tasks", body={"title": "Only title"})
    res = myfirstlambdaapi.lambda_handler(event, None)
    assert res["statusCode"] == 400


# ── Get ───────────────────────────────────────────────────────────────────────

def test_get_task(table):
    created = json.loads(
        myfirstlambdaapi.lambda_handler(
            make_event("POST", "/tasks", body={"title": "T", "description": "D"}), None
        )["body"]
    )
    task_id = created["task_id"]

    res = myfirstlambdaapi.lambda_handler(make_event("GET", f"/tasks/{task_id}", task_id=task_id), None)
    assert res["statusCode"] == 200
    assert json.loads(res["body"])["task_id"] == task_id


def test_get_task_not_found(table):
    res = myfirstlambdaapi.lambda_handler(make_event("GET", "/tasks/ghost", task_id="ghost"), None)
    assert res["statusCode"] == 404


# ── List ──────────────────────────────────────────────────────────────────────

def test_list_tasks(table):
    myfirstlambdaapi.lambda_handler(make_event("POST", "/tasks", body={"title": "T1", "description": "D1"}), None)
    myfirstlambdaapi.lambda_handler(make_event("POST", "/tasks", body={"title": "T2", "description": "D2"}), None)

    res = myfirstlambdaapi.lambda_handler(make_event("GET", "/tasks"), None)
    assert res["statusCode"] == 200
    assert len(json.loads(res["body"])["tasks"]) == 2


# ── Update ────────────────────────────────────────────────────────────────────

def test_update_task(table):
    task_id = json.loads(
        myfirstlambdaapi.lambda_handler(
            make_event("POST", "/tasks", body={"title": "T", "description": "D"}), None
        )["body"]
    )["task_id"]

    res = myfirstlambdaapi.lambda_handler(
        make_event("PUT", f"/tasks/{task_id}", body={"status": "DONE"}, task_id=task_id), None
    )
    assert res["statusCode"] == 200
    assert json.loads(res["body"])["status"] == "DONE"


def test_update_task_not_found(table):
    res = myfirstlambdaapi.lambda_handler(
        make_event("PUT", "/tasks/ghost", body={"status": "DONE"}, task_id="ghost"), None
    )
    assert res["statusCode"] == 404


# ── Delete ────────────────────────────────────────────────────────────────────

def test_delete_task(table):
    task_id = json.loads(
        myfirstlambdaapi.lambda_handler(
            make_event("POST", "/tasks", body={"title": "T", "description": "D"}), None
        )["body"]
    )["task_id"]

    res = myfirstlambdaapi.lambda_handler(
        make_event("DELETE", f"/tasks/{task_id}", task_id=task_id), None
    )
    assert res["statusCode"] == 200


def test_delete_task_not_found(table):
    res = myfirstlambdaapi.lambda_handler(
        make_event("DELETE", "/tasks/ghost", task_id="ghost"), None
    )
    assert res["statusCode"] == 404
