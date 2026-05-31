import json
import logging
import os
import uuid
from datetime import datetime, timezone

import boto3

logger = logging.getLogger()
logger.setLevel(logging.INFO)

dynamodb = boto3.resource("dynamodb")
TABLE_NAME = os.environ["DYNAMODB_TABLE"]


def lambda_handler(event, context):
    method = event.get("httpMethod", "")
    path = event.get("path", "")
    task_id = (event.get("pathParameters") or {}).get("task_id")

    if path == "/health":
        return respond(200, {"status": "ok"})

    if method == "POST" and path == "/tasks":
        return create_task(event)

    if method == "GET" and path == "/tasks":
        return list_tasks()

    if method == "GET" and task_id:
        return get_task(task_id)

    if method == "PUT" and task_id:
        return update_task(task_id, event)

    if method == "DELETE" and task_id:
        return delete_task(task_id)

    return respond(404, {"error": "Not found"})


def create_task(event):
    body = json.loads(event.get("body") or "{}")
    if not body.get("title") or not body.get("description"):
        return respond(400, {"error": "title and description are required"})

    task = {
        "task_id": str(uuid.uuid4()),
        "title": body["title"],
        "description": body["description"],
        "status": "PENDING",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }

    table = dynamodb.Table(TABLE_NAME)
    table.put_item(Item=task)
    logger.info("Created task %s", task["task_id"])
    return respond(201, task)


def get_task(task_id):
    table = dynamodb.Table(TABLE_NAME)
    result = table.get_item(Key={"task_id": task_id})
    item = result.get("Item")
    if not item:
        return respond(404, {"error": "Task not found"})
    return respond(200, item)


def list_tasks():
    table = dynamodb.Table(TABLE_NAME)
    result = table.scan()
    return respond(200, {"tasks": result.get("Items", [])})


def update_task(task_id, event):
    body = json.loads(event.get("body") or "{}")
    if not body:
        return respond(400, {"error": "Nothing to update"})

    table = dynamodb.Table(TABLE_NAME)
    body["updated_at"] = datetime.now(timezone.utc).isoformat()

    update_expr = "SET " + ", ".join(f"#k{i} = :v{i}" for i in range(len(body)))
    attr_names = {f"#k{i}": k for i, k in enumerate(body)}
    attr_values = {f":v{i}": v for i, (_, v) in enumerate(body.items())}

    try:
        result = table.update_item(
            Key={"task_id": task_id},
            UpdateExpression=update_expr,
            ExpressionAttributeNames=attr_names,
            ExpressionAttributeValues=attr_values,
            ConditionExpression="attribute_exists(task_id)",
            ReturnValues="ALL_NEW",
        )
        return respond(200, result["Attributes"])
    except dynamodb.meta.client.exceptions.ConditionalCheckFailedException:
        return respond(404, {"error": "Task not found"})


def delete_task(task_id):
    table = dynamodb.Table(TABLE_NAME)
    try:
        table.delete_item(
            Key={"task_id": task_id},
            ConditionExpression="attribute_exists(task_id)",
        )
        return respond(200, {"message": f"Task {task_id} deleted"})
    except dynamodb.meta.client.exceptions.ConditionalCheckFailedException:
        return respond(404, {"error": "Task not found"})


def respond(status_code, body):
    return {
        "statusCode": status_code,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(body, default=str),
    }
