import os
import json
import openai
import boto3
from dotenv import load_dotenv
from fastapi import HTTPException, Depends
from datetime import datetime, timedelta, timezone
from repositories.policy_repository import PolicyRepository
from schemas.prompt_schema import PromptChatStreamResponseSchema, CreatePromptResponseSchema

class PolicyService:
    def __init__(self, policy_repository: PolicyRepository = Depends()):
        self.policy_repository = policy_repository

    def extract_policy_by_cloudtrail(self):
        # 1. cloudtrail 로그 가져오기 (기간? 일단 일주일)

        # 2. policy 추출
        all_policies = []
        for log_entry in logs:
            if not isinstance(log_entry, dict):
                print("Error: Log entry is not a valid dictionary.")
                continue

            event_source = log_entry.get("eventSource")
            event_name = log_entry.get("eventName")

            if event_source == 's3.amazonaws.com':
                policy_data = await self.policy_repository.find_policy("S3", event_name)
                if policy_data is not None:
                    policy = s3_policy_mapper(log_entry, policy_data)
                else:
                    policy = map_etc(event_source, event_name)
                
                if policy:
                    all_policies.append(policy)

            elif event_source == 'ec2.amazonaws.com':
                policy_data = await self.policy_repository.find_policy("EC2", event_name)
                if policy_data is not None:
                    policy = ec2_policy_mapper(log_entry, policy_data)
                else:
                    policy = map_etc(event_source, event_name)
                
                if policy:
                    all_policies.append(policy)

            elif event_source == 'iam.amazonaws.com':
                policy = iam_policy_mapper(log_entry)
            
                if policy:
                    all_policies.append(policy)

            else:
                policy = map_etc(event_source, event_name)
                all_policies.append(policy)

        if not all_policies:
            print("No valid policies were generated.")
            return

        final_policy = merge_policies(all_policies)
        return final_policy