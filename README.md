<div align="center">

# AI Operations Platform

**Единая операционная платформа для wellness-клиник, медицинских спа и отелей**

[![TypeScript](https://img.shields.io/badge/TypeScript-5.x-3178C6?style=flat-square&logo=typescript&logoColor=white)](https://www.typescriptlang.org/)
[![Python](https://img.shields.io/badge/Python-3.12-3776AB?style=flat-square&logo=python&logoColor=white)](https://python.org)
[![Next.js](https://img.shields.io/badge/Next.js-14-000000?style=flat-square&logo=next.js&logoColor=white)](https://nextjs.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.111-009688?style=flat-square&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![Supabase](https://img.shields.io/badge/Supabase-Postgres-3ECF8E?style=flat-square&logo=supabase&logoColor=white)](https://supabase.com)
[![Claude](https://img.shields.io/badge/Claude-Sonnet_4.6-D97757?style=flat-square&logo=anthropic&logoColor=white)](https://anthropic.com)
[![License](https://img.shields.io/badge/license-MIT-green?style=flat-square)](LICENSE)

</div>

---

## Обзор

AI Operations Platform — production-ready монорепозиторий для автоматизации операций в сфере велнес и гостеприимства. Платформа объединяет CRM, управление бронированиями, клинические записи, биллинг, многоканальные коммуникации и AI-ассистента для персонала в едином решении.

**Для кого:** 10–200 сотрудников, 5–500 одновременных гостей, одна или несколько локаций.

### Ключевые возможности

| Модуль | Описание |
|---|---|
| **CRM и лиды** | Автоматическая классификация лидов через AI, воронка, профили гостей с шифрованием PII |
| **Бронирования** | Полный жизненный цикл: создание → подтверждение → чекин → чекаут, обнаружение конфликтов |
| **Клинические записи** | Безопасное хранение медицинских данных с RLS-изоляцией по арендатору |
| **Биллинг** | Пакеты услуг, Stripe-интеграция, автоматические напоминания о просроченных платежах |
| **AI Copilot** | RAG-ассистент для персонала: поиск по базе знаний, резюме истории гостя, подсказки по SOP |
| **Коммуникации** | Email (SendGrid), SMS и WhatsApp (Twilio), автоматизированные последовательности |
| **Аналитика** | Утилизация, выручка, конверсия апселлов — ночная агрегация через фоновый воркер |

---

## Архитектура

```
┌─────────────────────────────────────────────────────────────────┐
│                        apps/admin                               │
│              Next.js 14  ·  TypeScript  ·  Tailwind             │
│         Staff Dashboard: CRM, Schedule, Billing, Copilot        │
└────────────────────────┬────────────────────────────────────────┘
                         │ HTTP / Supabase Realtime
          ┌──────────────┼──────────────┐
          ▼              ▼              ▼
  ┌───────────────┐ ┌─────────┐ ┌──────────────┐
  │ services/     │ │Supabase │ │ services/    │
  │  ai-core      │ │Postgres │ │  worker      │
  │ FastAPI + RAG │ │+pgvector│ │  ARQ + Redis │
  └───────┬───────┘ └────┬────┘ └──────┬───────┘
          │              │             │
          ▼              ▼             ▼
      Claude API     Row-Level     AWS SQS
    OpenAI Embeds    Security      Outbox
      LangChain     11 schemas    Stripe / Twilio
                                  SendGrid / Notion
```

Платформа спроектирована вокруг **11 bounded contexts** (CRM, гости, бронирования, расписание, клиника, биллинг, коммуникации, база знаний, аналитика, аудит, общее). Каждый контекст — отдельная Postgres-схема с собственными RLS-политиками.

---

## Стек технологий

### Frontend
- **Next.js 14** (App Router) + **TypeScript** + **Tailwind CSS**
- **Radix UI** — доступные, компонуемые примитивы
- **React Query** (@tanstack) — серверное состояние
- **React Hook Form** + **Zod** — типобезопасные формы и валидация

### AI-сервис
- **FastAPI** (Python 3.12) — высокопроизводительный async API
- **Anthropic Claude** (`claude-sonnet-4-6`) — ядро рассуждений
- **OpenAI** (`text-embedding-3-small`) — векторные эмбеддинги для RAG
- **LangChain 0.2+** — агентные потоки и RAG-пайплайн

### Инфраструктура
- **Supabase** — Postgres + pgvector + Auth + Realtime + Storage
- **ARQ + Redis** — фоновые задачи и cron-джобы
- **AWS SQS + Lambda** — надёжные очереди и webhook-обработчики
- **Stripe** — платежи и инвойсы
- **Twilio** — SMS и WhatsApp
- **SendGrid** — транзакционный email

### Автоматизация
- **n8n** — сложные воркфлоу (Notion sync, эскалации)
- **Make** — визуальные коммуникационные сценарии
- **Zapier** — интеграции третьих сторон

---

## Структура репозитория

```
.
├── apps/
│   └── admin/                  # Staff dashboard (Next.js 14)
├── services/
│   ├── ai-core/                # AI API (FastAPI + LangChain + Claude)
│   └── worker/                 # Background jobs (ARQ + Redis)
├── packages/
│   ├── shared-types/           # Zod-схемы и TypeScript-типы
│   └── prompts/                # Промпт-шаблоны (без деплоя)
├── infra/
│   └── db/
│       ├── migrations/         # SQL-миграции (Supabase CLI)
│       └── seeds/              # Начальные данные
├── automations/
│   ├── n8n/                    # Воркфлоу-конфиги
│   ├── make/                   # Blueprints
│   └── zapier/                 # Документация интеграций
├── docs/                       # Проектная документация
│   ├── PRD.md
│   ├── ARCHITECTURE.md
│   ├── DATA_MODEL.md
│   ├── SECURITY.md
│   └── ADR/                    # Architecture Decision Records
├── ROADMAP.md                  # 90-дневный план
├── TICKETS.md                  # MVP-тикеты
└── .env.example                # Все переменные окружения
```

---

## Быстрый старт

### Требования

- **Node.js** 20+ и **npm** 10+
- **Python** 3.12+
- **Docker** и **Docker Compose**
- **Supabase CLI** (`npm install -g supabase`)

### 1. Клонирование и зависимости

```bash
git clone https://github.com/dmitriidrugov/ai-operations-platform.git
cd ai-operations-platform
npm install
```

### 2. Переменные окружения

```bash
cp .env.example .env.local
```

Заполните обязательные ключи в `.env.local`:

```env
# Supabase
NEXT_PUBLIC_SUPABASE_URL=https://your-project.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=...
SUPABASE_SERVICE_ROLE_KEY=...

# AI
ANTHROPIC_API_KEY=sk-ant-...
OPENAI_API_KEY=sk-...

# AWS
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=...
AWS_SECRET_ACCESS_KEY=...

# Redis
REDIS_URL=redis://localhost:6379/0
```

### 3. База данных

```bash
supabase start          # Запуск локального Supabase
npm run db:migrate      # Применение миграций
```

### 4. Запуск сервисов

```bash
# Все сервисы через Turbo
npm run dev

# Или по отдельности:
cd apps/admin       && npm run dev                          # → http://localhost:3001
cd services/ai-core && uvicorn main:app --reload --port 8000
cd services/worker  && arq main.WorkerConfig
```

---

## Скрипты

| Команда | Описание |
|---|---|
| `npm run dev` | Запуск всех сервисов через Turbo |
| `npm run build` | Сборка всех пакетов |
| `npm test` | Тесты (Vitest + Pytest) |
| `npm run lint` | ESLint + Ruff |
| `npm run db:migrate` | Применение SQL-миграций |
| `npm run db:generate-types` | Генерация TypeScript-типов из Supabase |

---

## Принципы безопасности

- **RLS как граница безопасности** — мультиарендная изоляция на уровне Postgres, JWT-клеймы прошиты в политики
- **Шифрование PII** — персональные данные гостей зашифрованы на уровне приложения
- **Outbox-паттерн** — каждый внешний сайд-эффект проходит через таблицу `outbox` в БД, гарантируя отсутствие потери данных
- **Защита от prompt injection** — пользовательский текст всегда в роли `user`, никогда в `system`
- **Детерминированность критичного кода** — биллинг, расписание и валидация никогда не делегируются AI

Подробнее: [`docs/SECURITY.md`](docs/SECURITY.md)

---

## Документация

| Документ | Содержание |
|---|---|
| [`docs/PRD.md`](docs/PRD.md) | Продуктовые требования, роли пользователей, пользовательские сценарии |
| [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) | Высокоуровневый дизайн, bounded contexts |
| [`docs/APPLICATION_DESIGN.md`](docs/APPLICATION_DESIGN.md) | API-дизайн, модели запросов/ответов |
| [`docs/DATA_MODEL.md`](docs/DATA_MODEL.md) | Полные связи сущностей и схемы |
| [`docs/AUTOMATION_LAYER.md`](docs/AUTOMATION_LAYER.md) | Стратегия интеграции n8n, Make, Zapier |
| [`docs/SECURITY.md`](docs/SECURITY.md) | Аутентификация, RLS, шифрование, управление секретами |
| [`docs/ADR/`](docs/ADR/) | Architecture Decision Records |
| [`ROADMAP.md`](ROADMAP.md) | 90-дневный план разработки MVP |
| [`TICKETS.md`](TICKETS.md) | Детальный список задач для MVP |

---

## Деплой

| Сервис | Платформа |
|---|---|
| Admin App | Vercel |
| AI Core | AWS ECS Fargate |
| Worker | AWS ECS Fargate |
| Database | Supabase (managed Postgres) |
| Queues | AWS SQS + Lambda |
| Secrets | AWS Secrets Manager (staging/prod) |
| Логи | AWS CloudWatch + OpenTelemetry |

---

## Лицензия

MIT © 2026 Dmitrii Drugov
