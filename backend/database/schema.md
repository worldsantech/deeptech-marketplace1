# MachinaHub Database Schema

## Core Tables

### users
- id
- email
- password_hash
- full_name
- role
- created_at

### organizations
- id
- name
- type
- country
- website
- created_at

### organization_members
- id
- organization_id
- user_id
- role

---

## Profiles

### engineer_profiles
- id
- user_id
- title
- bio
- hourly_rate
- years_experience
- country
- availability

### engineer_skills
- id
- engineer_profile_id
- skill_name
- level

### factory_profiles
- id
- organization_id
- overview
- country
- city
- lead_time_days
- min_order_quantity

### factory_equipment
- id
- factory_profile_id
- machine_name
- machine_type
- manufacturer
- model

---

## Projects

### projects
- id
- client_id
- title
- description
- category
- budget_min
- budget_max
- deadline
- status

### project_files
- id
- project_id
- file_name
- file_url
- file_type

### proposals
- id
- project_id
- engineer_profile_id
- cover_letter
- bid_amount
- estimated_days
- status

---

## Manufacturing

### rfqs
- id
- client_id
- title
- description
- material
- quantity
- deadline
- status

### rfq_files
- id
- rfq_id
- file_name
- file_url

### quotes
- id
- rfq_id
- factory_profile_id
- price_total
- currency
- lead_time_days
- status

---

## Collaboration

### contracts
- id
- contract_type
- source_id
- client_id
- supplier_id
- total_amount
- status

### milestones
- id
- contract_id
- title
- amount
- due_date
- status

### conversations
- id
- related_type
- related_id

### messages
- id
- conversation_id
- sender_user_id
- message_text
- created_at

---

## Trust

### reviews
- id
- contract_id
- reviewer_id
- reviewee_id
- rating
- comment