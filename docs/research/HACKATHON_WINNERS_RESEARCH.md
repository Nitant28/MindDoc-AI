# MindDoc AI: Hackathon Winners Research and Product Strategy

*Research date: 2026-11-09. Scope: Microsoft, Google and NVIDIA competitions, 2023 to 2026, plus Palantir's public AIP, Foundry and Ontology material.*

---

## 0. TL;DR

- **Winners attach a real, named user to a measurable outcome.** Champions almost always name one specific person with one painful problem (blind students, ALS patients, EMTs, creators whose designs get copied). They show traction or a metric ("users in 45 countries", "used in six schools", "WER 19.0% vs 32.7%").
- **They close the loop from insight to action.** The strongest 2025–2026 winners don't stop at answering questions. They *do* something: auto-calling hospitals (Medicall), automating takedowns (CopyFlag), syncing test cases to Jira (Skippers), flagging supply-chain risk (RiskWise).
- **Offline/edge and trust are rewarded on their own.** Google/Kaggle Gemma challenges overwhelmingly reward on-device, offline builds. Many prizes go to verification, explainability and "acts only with permission" designs (ModelProof, Tracer, Acuífero·Vigía, VibeCat, Team Zenith).
- **Judging is moving toward business readiness.** Imagine Cup 2027 now scores *enterprise customer validation, investability, technical excellence, customer value*. It also requires real Azure usage across 10 services. NVIDIA scores *real-world application + technology integration + submission quality*.
- **Palantir values a typed ontology (objects, links, actions), human-in-the-loop decisions with writeback, granular security applied equally to humans and agents, full audit/lineage, and evals.** MindDoc already has the raw pieces: knowledge graph, PII guardrails, hybrid retrieval and a CV/OCR pipeline. The gap is turning them into a **governed decision workflow** with pixel-level provenance and measured accuracy.

**Verification legend used below:**
- **[V]**: verified on an official or primary page fetched during this research.
- **[S]**: reported by a secondary source or a search-result snippet; not confirmed on a primary page.
- **[U]**: could not be verified.

---

## 1. Microsoft

### 1.1 Imagine Cup World Championship (2023–2026)

| Year | Placement | Project / Team | Country / Org | What it does | Key tech | Tags | Ver. |
|---|---|---|---|---|---|---|---|
| 2026 | **World Champion** ($150k + Satya Nadella mentorship) | **CopyFlag** (Patrick Brown) | UK (founder from Oxford [S]) | Detects copies of designs online, including **AI-altered** versions, and **automatically starts takedowns**. "Tested by thousands of creators", "tens of thousands of infringements" found [S] | Azure AI (specifics not published) | CV, GenAI, agentic action | [V] champion/desc; [S] traction |
| 2026 | World Finalist | **Revora Health** (agent "Clara") | US | AI rehab/physical-therapy platform: 24/7 triage, recovery plans, CV-based exercise form feedback, links to licensed providers | Azure-powered AI agent; Azure Health Data Services [S] | CV, agents, health | [V] / [S] |
| 2026 | World Finalist | **SpoilSafe** | US | Predicts cold-chain food spoilage from sensor data | Sensors + ML; Azure IoT Hub, Azure Data Explorer, Azure AI [S] | ML, IoT | [V] / [S] |
| 2025 | **World Champion** ($100k) | **Argus** (Arjun Oberoi, Daniel Kim) | Stanford, US | Clip-on glasses wearable for low-vision users: recognizes faces, objects (e.g., pills), helps navigation by voice command. Hybrid edge+cloud to cut latency; plans FDA path | Wi-R body-area link, edge + cloud AI, Azure AI Speech, Azure OpenAI (image analysis) | CV, edge, GenAI | [V] |
| 2025 | Runner-up ($25k) | **Signvrse** | Kenya (ALU, USIU, Machakos, TU Mombasa) | Speech/text → Kenyan Sign Language via 3D avatar; **used in six schools** | Azure AI Speech, custom motion-capture KSL dataset, 3D avatars | GenAI, CV data | [V] |
| 2025 | Runner-up ($25k) | **HairMatch** | UNC Chapel Hill / Georgia Tech, US | Scans hair to classify type/porosity, recommends products; **users in 45 countries** | GPT-4o on Azure AI Foundry (vision) | CV, GenAI | [V] |
| 2024 | **World Champion** ($100k) | **FROM YOUR EYES** | Turkey | **Mobile app + API** giving visually impaired users fast, detailed visual explanations | GPT-4 + own image-recognition models | CV, GenAI, API product | [V] |
| 2024 | World Finalist | **JRE** | UK | Slag detection in steel continuous casting (yield + quality) | Azure ML, Microsoft Fabric, Copilot | ML, industrial | [V] |
| 2024 | World Finalist | **PlanRoadmap** | US | AI productivity coach for people with ADHD task paralysis | Azure OpenAI | GenAI | [V] |
| 2023 | **World Champion** ($100k) | **TAWI** | Kenya (USIU-Africa) | Home app helping children with Auditory Processing Disorder build listening skills | Noise cancellation, sound amplification, speech-to-text | ML, accessibility | [V] |
| 2023 | World Finalist | **Eupnea** | US | Low-cost tuberculosis solution for patients and providers | Not stated | Health | [V] |
| 2023 | World Finalist | **CS-M Tool** | Thailand | Medical device for regular cardiac self-monitoring | Not stated | Health, device | [V] |

**Notable 2026 semifinalists relevant to MindDoc** [V]:
- **Nyck AI**: procurement agent on existing ERPs.
- **SIER (Sidekick)**: wearable with automated compliance reporting.
- **Retribution (CareOrbit)**: multi-agent care coordination that flags drug interactions.
- **IONMONKS**: explainable AI investment guidance.
- **HaptE**: edge cameras on forklifts.
- **Team Recall**: zero-typing inventory copilot.

**How Imagine Cup is judged (evolution):**
- **2024** [S]: judges looked "beyond innovation" to responsible AI use, accessibility and business viability.
- **2026** [S, from staging FAQ snippet]:
  - Microsoft cloud and AI technology implementation
  - Inclusive design
  - Viability
  - Founder-led validation and continuous improvement
- **2027 season (opened Nov 2026)** [V, FAQ]: now **open to all early-stage startups**, with 7 categories plus a Student Startup prize. Judging runs in three stages:
  1. **Application review:** startup/business profile, product and technical approach, problem and market opportunity, team execution.
  2. **Expert review:** business readiness, technical excellence, customer value (from pitch deck, demo, Azure architecture, written answers).
  3. **Final judging:** **enterprise customer validation, investability, technical excellence, customer value**.
  - The technical explanation must cover architecture, Azure services, **security, reliability and scalability**, technical differentiation and product maturity.
  - The entry must show **at least $1 of spend on 10 unique Azure services**.
  - GeekWire reports that diversity, inclusion and accessibility were dropped from the criteria for 2027 [S].

### 1.2 Microsoft AI Agents Hackathon 2025 (Apr 8–30, 2025; 570 submissions, 18,000+ registrants) [V]

Judging criteria: innovation, impact, usability, solution quality, category alignment.

| Award | Project | What it does | Key tech |
|---|---|---|---|
| **Best Overall** | **RiskWise** | Agents scan shipping schedules and trade news to flag supply-chain risks (port delays, geopolitics) | Azure AI Agent Service, Semantic Kernel, SQL, Next.js |
| Best C# | **Apollo** | Deep-research meta-agent: a coordinator directs sub-agents and produces research reports | Semantic Kernel, multi-agent group chat, **self-reflective RAG**, pgvector |
| Best Java | **Bit2Brain** | Captures learning snippets from links/video/images into an interactive "Knowledge Star Map" | LangChain4j, Azure Video Indexer, **Azure Computer Vision, Neo4j** |
| Best Copilot | **WorkWizee** | Automates P1/P2 incident handling in Teams (Jira tickets, Bitbucket PRs, notifications) | Copilot Studio, Azure Functions |
| Best JS/TS | **ModelProof: Sentinel AI Chat** | Runs **two LLMs per query, compares answers, audits for hallucination, bias, toxicity** | Azure OpenAI + second model, content moderation |
| Best Azure AI Agent Service | **TARIFFED!** | Plain-language tariff Q&A grounded in a SQL tariff DB + Bing grounding | Azure AI Agent Service, .NET 9, SQL Server |
| Best Python | **Konveyor** | Captures expert knowledge from documents and Q&A for later querying (knowledge transfer) | Semantic Kernel, vector DB |

Related [S]: Power Platform "Powerful Devs Hack Together 2025" Best Overall was **CardioTriage AI** (search snippet only).

### 1.3 Microsoft AI Classroom Hackathon (Oct 26 – Dec 5, 2023; winners May 2024) [V]

Judging: use of core Azure components (AI, databases, app services), plus **bonus credit for accessibility and Microsoft Responsible AI principles**.

| Award | Project | Team / Country | What it does | Tech |
|---|---|---|---|---|
| 1st (Technical) | **ChatEDU** | Vanderbilt, US | Turns any text/file into a tutoring session: study guides, practice tests | Azure AI (GPT-4), Azure DBs |
| 2nd | **Dialogues Through Time** | Munich, DE | History game with AI dialogue + visuals | Not stated |
| 3rd | **Insight** | Singapore | Upload lecture notes → personalized quizzes/flashcards | Not stated |
| Best Undergrad | **DevHub** | Pakistan | ML-based mentorship/career roadmap app | ML |
| Best Graduate | **Cuepal** | US | Notes → flashcards/quiz questions | GPT-4 |
| Best No-Code | **Neural Synchronisation** | India | Real-time feedback on group discussion; detects speech dominance | Azure Cognitive Services (transcription) |
| Honorable | **EquEdu** | (visually impaired developer) | Makes online educational content accessible | AI (unspecified) |

> Observation: three of the seven winners turn **uploaded documents into structured learning artefacts**. "Chat with your PDF" alone was already table stakes in 2023.

---

## 2. Google

### 2.1 Google Solution Challenge (UN SDGs, students)

| Year | Placement | Project / Team | Country / Uni | What it does | Google tech | Ver. |
|---|---|---|---|---|---|---|
| 2025 (APAC edition, ADB + Hack2skill, Manila, Jun 25–26; ~750 teams, 12 countries) | **Top 3** | **Medicall** (Team Atempo) | Konkuk Univ., South Korea | EMTs enter location + symptoms. Gemini picks suitable hospitals, the app **auto-calls them via ARS**, connects to the first that accepts, then navigates | Gemini, Flutter, GCP, Maps API | [V] |
| 2025 | **Best AI Use Case** award | **GeoGemma** | Institute of Space Technology, Pakistan | Geo-LLM: surface temperature, forest loss etc. for any location | Gemini + geospatial data | [S] (Gulf News) |
| 2025 | People's Choice / Most Societal Impact | Unnamed Philippine team / unnamed South Korean team | – | – | – | [S] names [U] |
| 2025 | Top 10 | Guardy (Korea Univ.), VitalTrip (Kyungpook Natl. Univ.) | South Korea | – | – | [V] |
| 2024 | **Winning 3** | **ATTI** | Pukyong Natl. Univ., South Korea | Voice-assistant app helping people with mild dementia manage memory and routines | Flutter, Firebase, GCP, **Gemini API** | [V] |
| 2024 | **Winning 3** | **Spoon Share** | Deogiri Institute (Aurangabad), India | Food donors ↔ people in need; map; **organizations verify listings** | Flutter, Firebase, Maps | [V] |
| 2024 | **Winning 3** | **Alpha-Eye** | LAUTECH, Nigeria | AI app for early eye-disease detection (Sub-Saharan Africa) | ReactJS, Flutter, Python, GCP | [V] |
| 2024 | People's Choice | **Saheli** | NIT Jalandhar, India | Women's safety app: SOS, safe navigation, **offline access**, chatbot guide | Flutter, Firebase, GCP, Gemini API | [V] |
| 2023 | **Top 3** | **Wonder Reader** | BINUS, Indonesia | 3D-printed digital braille device; teacher sends questions over Bluetooth | Google Cloud, Firebase, Flutter, TTS API | [V] |
| 2023 | **Top 3** | **BuzzBusters** | UAGRM, Bolivia | Early warning for mosquito-borne pathogens | **Vertex AI, TensorFlow**, Firebase, Maps, Colab | [V] |
| 2023 | **Top 3** | **HeadHome** | NTU, Singapore | App for dementia-wandering patients and caregivers | Cloud Run, Maps, Firebase | [V] |

Prize: $3,000 per member for Winning 3 (2023–2024) [V/S]. The full official 2025 Top 3 list was **not found**. Only Medicall is confirmed as Top 3.

### 2.2 Gemini API Developer Competition (May 15 – Aug 12, 2024; winners Nov 21, 2024) [V]

Judging (reported) [S]: remarkability, creativity, usefulness, impact, execution. Prizes (reported) [S]: Best Overall = custom electric DeLorean; Most Impactful top cash $300k; Most Useful and Most Creative $200k each. Developer names/countries are not given in Google's announcement.

| Award | App | What it does | Key tech |
|---|---|---|---|
| **Best Overall** | **Jayu** | Personal assistant that works across browser, code editor, music, games; **interprets screen visually, interacts with app UIs**, real-time translation | Gemini visual understanding (screen agent) |
| **Most Impactful + People's Choice** | **Vite Vere** | Step-by-step guidance for people with cognitive disabilities | Gemini vision + prompting |
| **Most Useful + Best Flutter** | **Prospera** | Real-time AI sales coach: analyses calls, feedback, performance reports | Gemini, Flutter |
| Most Creative | **Outdraw AI** | Draw what humans recognize but AI can't | Gemini vision |
| Best Android | **Gaze Link** | Eye tracking + Gemini lets ALS patients turn single words into full sentences | Gemini, Android, eye tracking |
| Best Web | **ViddyScribe** | Auto audio-description of videos for blind users | Gemini multimodal |
| Best Game | **Pen Apple** | Deck-builder where Gemini Flash interprets card effects | Gemini Flash |
| Best Firebase | **Trippy** | Personalized travel planning | Gemini, Firebase |
| Best ARCore | **Everies** | Animates everyday objects via AR + generated scripts | Gemini vision, ARCore |

### 2.3 Kaggle / Google open-model challenges (2025–2026) [V]

**Gemma 3n Impact Challenge** (winners Dec 10, 2025; 600+ submissions). Every winner is on-device/offline:

| Place / Prize | Project | What it does | Key tech |
|---|---|---|---|
| 1st (+ Google AI Edge prize) | **Gemma Vision** | Chest-mounted phone camera assistant for blind users; built with a visually impaired user | MediaPipe LLM Inference, flutter_gemma, on-device |
| 2nd | **Vite Vere Offline** | Offline version of the 2024 Gemini winner; images → simple spoken instructions | Gemma 3n offline + TTS |
| 3rd | **3VA** | AAC: pictograms → rich expressions for a designer with cerebral palsy | Gemma 3n fine-tuned locally (Apple MLX) |
| 4th | **Sixth Sense for Security Guards** | Distinguishes real threats from harmless motion across 16 cameras | **YOLO-NAS detector → Gemma 3n contextual reasoning** |
| Unsloth | **Dream Assistant** | Voice assistant for speech-impaired users | Fine-tuned on the user's own audio |
| Ollama | **LENTERA** | Offline micro-server + Wi-Fi hotspot education hub | Ollama |
| LeRobot | Graph-based Cost Learning + Gemma 3n | Robot sensing/planning | LeRobot, IGMC |
| NVIDIA Jetson | **My (Jetson) Gemma** | Context-aware voice interface | Jetson Orin |

**MedGemma Impact Challenge** (winners Mar 26, 2026; 850+ teams). Document and record extraction features heavily:

| Place / Prize | Project | What it does | Key tech |
|---|---|---|---|
| 1st | **EpiCast** | Health-worker **local-language observations → structured WHO IDSR surveillance signals** | Fine-tuned MedGemma, MedSigLIP, HeAR |
| 2nd | **Sunny** | Skin-change photos → **structured reports**, privacy-protecting | Fine-tuned MedGemma, mobile |
| 3rd | **FieldScreen AI** | **Offline** TB screening from chest X-ray + cough audio | MedGemma, HeAR, MedASR, TranslateGemma |
| 4th | **Tracer** | Flags possible medical errors by **comparing hypotheses in physician notes with incoming test results**, with confidence scoring | MedGemma, document extraction |
| Novel Task | **ClinicDx** | Offline diagnostics **inside OpenMRS (EHR)**, grounded in 160+ WHO/MSF guidelines | Fine-tuned MedGemma |
| Novel Task | **UniRad3s** | Radiology: Spot, Segment (3D), Simplify patient reports | MedGemma, MedSAM2 |
| Edge AI | **BridgeDx** | Offline decision support from WHO/MSF/Orphanet guidelines | Edge |
| Agentic Workflow | **CaseTwin** | Matches chest X-rays to historical "twins" to speed rural referrals | Agentic |
| Agentic Workflow | **BigTB6** | Voice-driven TB/anemia screening (cough, X-ray, pallor) | Multimodal |

**Gemma 4 Good Challenge** (winners Aug 24, 2026; 1,600+ submissions), selected winners:

| Place / Prize | Project | What it does | Key tech |
|---|---|---|---|
| 1st | **GEM-4** | Robotic assistant for elderly/disabled | Gemma 4 VLA, CV |
| 2nd | **Trido** | Voice-controlled whiteboard for teachers, offline fallback | Local Gemma 4 E2B |
| 3rd | **PenguinAgent** | Offline wildlife dashboard: field video + telemetry + **RAG over scientific papers** | Gemma 4 26B, SAM 3, SigLIP 2 |
| Global Resilience | **Acuífero·Vigía** | Offline flood early warning on Raspberry Pi 5, **auditable reasoning** | Gemma 4 E2B, sensor fusion |
| AI Trust & Safety | **TrueVoice** | On-device voice-clone scam detection | Gemma 4 E4B audio |
| Digital Equity | **Gem-Care** | Dysarthric speech reconstruction, **WER 19.0% vs 32.7% baseline** | Fine-tuned Gemma 4 |
| Education | **CodeBuddy** | Socratic tutor from **photos of handwritten code**, teacher dashboard | Gemma 4 E4B, offline OCR |
| llama.cpp | **PreVillage** | Voice-first WhatsApp navigator for govt services in rural Nepal, **local RAG with self-healing loop**, 7.5 tok/s on Pi 5 | llama.cpp |
| Ollama | **PathOS** | Offline histopathology screening; GRPO-trained | Gemma 4 E2B |

### 2.4 Google Cloud hackathons (2025–2026) [V]

**Agent Development Kit (ADK) Hackathon** (results Sep 2, 2025; 10,400+ participants, 477 projects):
- **Grand Prize: SalesShortcut.** Multi-agent SDR that handles lead research, proposals and outreach.
- **Regional winners:**
  - Energy Agent AI (NA)
  - **Edu.AI** (LatAm): agents grade essays and build study plans and mock exams.
  - **GreenOps** (APAC): audits, forecasts and optimizes cloud infrastructure for sustainability.
  - Nexora-AI (EMEA)
- **Honorable mentions:** Particle Physics Agent, **TradeSageAI** (multi-agent financial analysis), Bleach (visual agent builder).

**Gemini Live Agent Challenge** (May 16, 2026; 1,536 projects, 151 countries):
- **Grand Prize: ORION.** Voice-directed surgical co-pilot that gives live data and visual assistance without the surgeon breaking scrub.
- **Category winners:**
  - drone-copilot
  - Sankofa
  - Moonwalk (hands-free desktop agent)
  - Wand (voice + gesture)
  - JohnKeats.AI
  - Rayan Memory
- **Honorable mentions:**
  - NagarDrishti (voice civic reporting + official dashboard)
  - Ekaette
  - **VibeCat** (watches the screen and **acts only with permission**)
  - Call My Parts
  - Relay

**Gen AI Exchange Hackathon 2025 (India; Google Cloud + Hack2skill; finale Nov 29, 2025; 270k+ developers).** This includes the closest direct competitor archetype to MindDoc:

| # | Track | Team | Project | What it does |
|---|---|---|---|---|
| 3 | **Demystifying Legal Documents** | Crewmate | **Legal SahAI** | Simplifies legal documents; **form assistant + lawyer-client portal**; RAG |
| 8 | Startup Evaluation | AIxpert | **PitchLense** | **Automated document parsing → risk reports**, analyst copilot, scoring |
| 6 | Test Case Generation | Skippers | (meta-automation) | **PRDs → traceable, GDPR-safe test cases synced to Jira** |
| 7 | Cement Operations | May The Agents Be With You | – | Agents optimize plant operations; **human operators approve high-level decisions** |
| 4 | Misinformation | Technopaths | **Parallax** | Deepfake detection incl. heartbeat signals in video; explainable |
| 10 | AI Governance | Success | – | ML risk prediction + policy agents + citizen transparency dashboards |

Other winners in that list: YouthMind, ArtisanGully, a career advisor and a trip planner.

---

## 3. NVIDIA

### 3.1 Generative AI Agents Developer Contest (NVIDIA × LangChain; May 15 – Jun 17, 2024; 500+ participants) [V]

Judging: (1) **real-world application**, (2) **technology integration** (NVIDIA LLM products + LangChain/LangGraph), (3) **quality of submission** (details, instructions, demo).

| Placement | Developer | Project | What it does / tech |
|---|---|---|---|
| Winner | Brian Caffey | **Agents of Inference** | LangGraph agent workflow that writes and renders a short spy film (cast, scenes, shots, images, video). Llama 3 NIM, Stable Diffusion / SVD, ffmpeg |
| Winner | Panna Felsen | **AI Personal Trainer** | Description not on winners page [U] |
| Winner | Malcolm White | **Mystery Manor** | Description not on winners page [U] |
| Honorable (10) | – | Persona (Unreal Engine), RGS Tool, L'Agent, LLM Trading Agent, VRM AI Facial Emotions, Aileen 2, Test Generator App, Satyuki the Code Mentor, Trainer's Ally, Narravive | Not described |

Discrepancy: UW-Milwaukee says Dr. Jake Luo's **CarePilot** (a healthcare-communication chatbot) was "one of the top three winners". It is not on NVIDIA's winners page, so this is self-reported [S].

### 3.2 NVIDIA × LlamaIndex Developer Contest (fall 2024) [V]

Judging: real-world novel application, technology integration. Entries had to use at least one of NIM, NeMo Retriever, NeMo Guardrails, NeMo Curator or TensorRT-LLM, plus LlamaIndex. Prizes: $5k / $3k / $1k, then RTX 4080 SUPER for 4th–6th.

| Placement | Developer | Project | What it does |
|---|---|---|---|
| Winner (listed 1st) | Oleksandr Arsentiev | **RetainAI** | Personalized employee-retention strategies |
| Winner (listed 2nd) | Matthew Williamson | **Plotomatic** | Python notebooks that generate a full story from one prompt |
| Winner (listed 3rd) | Dhruv Shah | **ESG Insights AI** | Page shows a copy-pasted description [U]; name implies ESG report analysis |
| Honorable | Lam Vo; Vincent Pisano; Muhammad Faisal; Derek Tang | RandomAI; RPG Teacher; **Sales Expert RAG System**; iPro | Story publishing; edu RPG; RAG over sales data; LOB search |

### 3.3 Gen AI on RTX PCs Developer Contest (Jan 8 – Feb 23, 2024) [V]

The winners page lists three projects but no descriptions:
- **OutlookLLM** (Francisco Gonzalez-Blanch)
- **CLARA** (Matthew Yaeger)
- **RocketLeague BotChat** (Brian Caffey)

The requirement was TensorRT / TensorRT-LLM on a Windows PC, i.e., local inference.

### 3.4 NVIDIA Agent Toolkit (AgentIQ / NeMo Agent Toolkit) Hackathon (May 12–23, 2025) [V]

| Project | Developer | What it does | Tech |
|---|---|---|---|
| **cuOptIQ** | Krishna Sai Tarun (TCS Smart Mobility) | Forklift route optimization agent with NL interface | NeMo Agent Toolkit + **cuOpt + Omniverse** |
| **OpenCodeReview** | Victor Tong | Open-source AI code security/vulnerability review | Agent Toolkit |
| **Holistic Travel Assistant** | Satej Sahu | Multi-agent flights/hotels/activities | Agent Toolkit multi-agent |

### 3.5 Edge AI: Hackster × SparkFun × NVIDIA AI Innovation Challenge (Jetson; winners Apr 26, 2024; $60k pool) [V]

| Category / Place | Developer | Project | Tech |
|---|---|---|---|
| GenAI Apps, 1st | Dave Niewinski | **Interactive Animatronic GLaDOS** | Jetson AGX Orin, Riva ASR, NeMo TTS, **local LLM**, stereo camera |
| GenAI Models for Edge, 1st | Andrei Ciobanu | **EdgeStyle** (virtual try-on) | Jetson Orin, **YOLOv5 + SAM + OpenPose + Stable Diffusion** |
| AI at the Edge Apps, 1st | Allen Tao | **An Eye for an Item** (find lost objects robot) | Jetson Orin, zero-shot detection, LLMs, NanoDB, Isaac ROS |
| GenAI Models, 2nd | Huy Mai | Realtime Language Segment Anything on Jetson Orin | SAM-style |
| Edge Open, 3rd | Team Kinetika | **Counting for Inspection & QC with TensorRT** | TensorRT |

Other placings: Escalator People Tracker, Local Cooking Assistant, ClearWaters, Robotic Shopping Cart.

### 3.6 NVIDIA Cosmos Cookoff (winners Apr 2026; 1,600+ participants [S]) [V]

| Place | Team | Project | What it does |
|---|---|---|---|
| 1st | Team Zenith | **See How It Thinks: Mixed Palletizing with Explainable Visual Reasoning** | Stacks mixed items and **explains its decisions** |
| 2nd | Team JARVIS | **ResQ-AI** | Autonomous disaster-response drone "Structural Scout" (sim-to-real) |
| 3rd | Team LiveKit | Voice Controlled AI Video Intelligence | Multi-camera feed selection with voice control |

### 3.7 GTC hackathons (2025 / 2026)

GTC San Jose 2026 (Mar 16–19) ran four hackathon events [V]:
- **Hack for Impact** (6 h; GB10 systems; open models; human/eco/culture impact)
- **Hack to Create** (creator tools)
- **Live Agent Gauntlet** (agents benchmarked live on a real-time leaderboard)
- **Vibe Hack** (Nemotron)

**No published winners were found for GTC 2025 or GTC 2026 hackathons [U].** The NVIDIA × Alibaba Tianchi 2025 China hackathon was not researched in detail.

---

## 4. Patterns that separate winners from the rest

| # | Pattern | Evidence (winners) | Implication for MindDoc |
|---|---|---|---|
| 1 | **A named user and a narrow job-to-be-done** | Argus (low vision), Gaze Link (ALS), Medicall (EMTs), TAWI (APD kids), CopyFlag (creators), Gemma Vision (co-designed with a blind user) | Pick **one vertical persona**, not "any document". Show the persona in the first 15 seconds |
| 2 | **Traction or validation beats features** | HairMatch "users in 45 countries"; Signvrse "six schools"; CopyFlag "thousands of creators"; Imagine Cup 2027 scores *enterprise customer validation* | Run a pilot with 3–5 real users and log usage; get letters of intent |
| 3 | **Quantified results** | Gem-Care WER 19.0% vs 32.7%; PreVillage 7.5 tok/s on Pi 5; Leaf Scope >90% (2023 finalist) | Publish an eval table: extraction F1, retrieval recall@k, faithfulness, latency, cost/doc |
| 4 | **Close the loop: insight → action** | Medicall auto-calls hospitals; CopyFlag auto-takedowns; Skippers syncs to Jira; WorkWizee files tickets; RiskWise flags risk; SalesShortcut does outreach | Every answer should be able to **trigger a governed action** (task, deadline, escalation, export, draft letter) |
| 5 | **Unstructured → structured is the real value** | EpiCast (notes → WHO signals), Sunny (photos → reports), Tracer (notes vs labs), PitchLense (docs → risk report), Bit2Brain (→ knowledge map) | Lead with **schema extraction into a typed graph**; chat is the secondary interface |
| 6 | **Trust, verification, explainability get their own prizes** | ModelProof (dual-LLM audit), Tracer (confidence), Acuífero·Vigía (auditable reasoning), Team Zenith (explainable), TrueVoice (Trust & Safety prize), VibeCat (acts only with permission) | Claim-level verification, abstention, confidence, and a "why" panel |
| 7 | **Human-in-the-loop by design** | Cement Ops ("operators approve high-level decisions"); Spoon Share (orgs verify listings); CodeBuddy teacher dashboard; Palantir AIP | Review queue + approve/reject actions; show the human as the final authority |
| 8 | **Offline / edge / privacy-first** | All Gemma 3n winners; FieldScreen, ClinicDx, BridgeDx (MedGemma); Argus hybrid edge+cloud; Saheli offline; NVIDIA RTX/Jetson contests | Sensitive docs → **local VLM/LLM mode** (MindDoc already ships Ollama/llama.cpp hooks); benchmark it |
| 9 | **Multimodality as a requirement** | Jayu (screen vision), ViddyScribe, Sixth Sense (YOLO + LLM), CodeBuddy (handwriting photos), UniRad3s (segmentation), EdgeStyle (YOLO+SAM+SD) | Combine **classical CV (layout, tables, signatures, stamps, tamper) + VLM reasoning**, as in the YOLO→LLM pattern |
| 10 | **Agentic, multi-agent architectures with grounding** | Apollo (self-reflective RAG), TARIFFED (SQL + web grounding), ADK winners, ClinicDx/BridgeDx (guideline-grounded), PreVillage (self-healing RAG) | Planner → retriever → verifier → actor, grounded in a playbook or regulation corpus |
| 11 | **Deep use of the sponsor's stack** | NVIDIA scores "technology integration"; Imagine Cup 2027 requires 10 Azure services; Google prizes per tool (Flutter, Firebase, ARCore, Ollama, LiteRT, Unsloth) | Keep a **provider-abstraction layer** so you can swap in Azure / Gemini / NIM per competition |
| 12 | **Demo and submission quality** | NVIDIA judges "quality of submission… demo"; Live Agent Gauntlet live leaderboard; Imagine Cup expert review of deck + demo + architecture | 3-minute scripted demo, architecture diagram, README with one-command run, recorded fallback video |
| 13 | **Platform/API, not just an app** | FROM YOUR EYES ("mobile app **and API**"); Bleach (agent builder); Palantir tools exposed to agents | Ship a REST/MCP endpoint so other agents can call MindDoc |
| 14 | **Shift from social-good to B2B in Microsoft's flagship** | 2023–2025 champions were accessibility/health; 2026 champion CopyFlag is B2B IP protection with automated enforcement; 2027 rules score investability | For Imagine Cup and VC-style judging, pitch ROI and customers. For Google/Kaggle, pitch social impact + edge |

---

## 5. What Palantir-style companies value (from public AIP / Foundry / Ontology docs)

| Principle | What Palantir says (paraphrased, with short quotes) | MindDoc translation |
|---|---|---|
| **Ontology as the operational layer** | Datasets/models are mapped into **object types, properties and link types**. It is often a "digital twin of the organization". Rows become objects, columns become properties, relationships become links | Replace generic "entities" with a **typed domain schema**: `Document → Page → Clause/Field`, `Party`, `Obligation`, `Deadline`, `Amount`, `Matter/Case` |
| **Semantic vs kinetic** | Semantic = what exists. Kinetic = **actions, functions, dynamic security**: change "while complying with organizational controls and governance" | Add **Action types** (Approve field, Flag risk, Create task, Escalate, Redact) with parameters, rules and submission criteria |
| **Decisions captured as data (writeback)** | Action types "capture data from operators". AIP Logic edits reach the Ontology **only when executed from an Action** (gated writeback) | Agents *propose*, humans *commit*. Every committed decision is stored and learnable |
| **Human-in-the-loop + autonomy mix** | AIP can "weave human-in-the-loop workflows with entirely autonomous operations". Agents follow the same change-management as humans. Workflows should identify human review points | Confidence-based routing: auto-accept high-confidence fields, queue the rest |
| **Security applied equally to agents** | **Role-, marking- and purpose-based** controls on every operation by humans *and* agents. **Markings** for PII/PHI | PII/PHI **markings on chunks and fields**, enforced inside retrieval (agent can't see what the user can't) |
| **Audit and lineage** | Every action by a human or agent is logged. Workflows are traceable step by step, with token/resource usage. Dataset lineage + transactional versioning | Per-answer **provenance record**: query → chunk IDs → page/bbox → OCR confidence → model + prompt hash → reviewer decision |
| **Evals as a product feature** | **AIP Evals**: test cases, compare LLMs, examine variance across runs. Built for non-determinism | Built-in eval suite + regression dashboard, run on every model/prompt change |
| **Document Intelligence specifically** | Compare **extraction strategies** (traditional OCR/layout vs VLM vs **OCR-preprocessed VLM**) on **quality, speed and token cost**. A VLM judge scores runs on a 1–5 rubric (tables, headers). One-click deploy to batch pipelines or per-page functions | Add a **strategy lab**: run Tesseract-only vs VLM vs hybrid on a sample and pick per document type with measured cost/quality |
| **Model-agnostic** | "Modular and extensible with respect to models, compute engines, and interfaces" | Keep the provider router (DeepSeek / OpenAI / Ollama / llama.cpp); add Azure/Gemini/NIM adapters |
| **Branching / review of changes** | Changes go through proposal → review → approval before merging | Schema and playbook changes versioned and reviewed (lightweight) |
| **Time-to-value** | AIP Bootcamps: "zero to use case" in 1–5 days on the customer's own data (company-reported outcomes) | Pitch: "Upload your 50 contracts; in 10 minutes you get an obligation register with sources" |

---

## 6. MindDoc AI baseline (from the current repo, for gap analysis)

What already exists, per module docstrings:
- **CV pipeline** (`app/vision/cv.py`):
  - quality assessment (blur, exposure, contrast)
  - preprocessing (denoise, CLAHE, deskew, threshold)
  - **layout analysis** (text blocks, ruling-line tables, figures)
  - OCR with **per-word confidence** (Tesseract/EasyOCR)
  - optional VLM captions
- **Hybrid retrieval** (`app/ml/retrieval.py`): BM25 + dense → RRF → optional cross-encoder rerank → MMR, with self-healing re-embedding.
- **Knowledge graph** (`app/ai/knowledge.py`): pattern + heuristic NER + LLM GraphRAG-style typed entities/relations, entity-linked chunk expansion.
- **Guardrails** (`app/ai/guardrails.py`): PII detection/redaction (incl. Luhn, PAN, Aadhaar) and **indirect prompt-injection detection** (OWASP LLM01).
- **Insights/extraction** (`app/ml/insights.py`, `app/ai/extraction.py`): classification, keywords, summaries, topic discovery, schema field extraction.
- **Local models**: Ollama / llama.cpp managers.

**Gap vs winners/Palantir:**
- no governed actions or decision capture
- no review queue
- citations not tied to page regions
- no published accuracy metrics
- generic rather than vertical schema
- no role/marking-aware retrieval
- no audit/provenance export
- no cross-document consistency checks

---

## 7. Prioritized features to adopt (22)

Labels: **CV**, **ML**, **GenAI**, **Product**, **RAI** (Responsible AI). Priority: **P0** = needed for any finals demo; **P1** = differentiator; **P2** = polish/scale.

| # | Pri | Feature / concept | Label | Inspired by | What the judge sees |
|---|---|---|---|---|---|
| 1 | P0 | **Pixel-level citations**: every answer/field links to page + **bounding box** highlighted on the original scan (OCR word boxes already exist) | CV, Product | Palantir lineage; Tracer; NVIDIA "submission quality" | Click a citation → the exact highlighted region on the scan |
| 2 | P0 | **Vertical ontology + schema extraction** into typed objects (e.g., Contract → Parties, Clauses, Obligations, Deadlines, Amounts) with per-field confidence | GenAI, ML | Palantir Ontology; EpiCast; PitchLense; Sunny | A structured register auto-built from 50 messy PDFs |
| 3 | P0 | **Confidence-routed human review queue** (OCR conf × extraction conf × verifier score), with accept/edit/reject | Product, RAI | Palantir HITL + gated writeback; Cement Ops; Spoon Share verification | "Only 12% of fields needed a human; here is the queue" |
| 4 | P0 | **Governed Actions that close the loop**: create deadline/calendar item, task/ticket (Jira/Trello), draft notice/email, export CSV/Excel, escalate. Agent proposes, human approves | GenAI (agentic), Product | CopyFlag takedowns; Medicall auto-calls; Skippers→Jira; WorkWizee; RiskWise | The demo ends with a real action, not a chat bubble |
| 5 | P0 | **Eval harness + public metrics page**: extraction F1 per field, retrieval recall@k/MRR, answer faithfulness, abstention accuracy, latency, **cost/doc**. Run on public sets (e.g., CUAD for contracts, FUNSD/SROIE for forms/receipts, DocVQA) | ML, RAI | Gem-Care WER table; AIP Evals; Palantir Doc Intelligence quality/speed/cost | A slide with numbers vs a baseline |
| 6 | P0 | **Claim-level verification and abstention**: split answer into claims, check each against cited chunks (NLI/LLM-judge), drop/flag unsupported claims, "not in documents" fallback. Optional dual-model cross-check | GenAI, RAI | ModelProof; Tracer; Acuífero·Vigía auditable reasoning | Green/amber/red support badge per sentence |
| 7 | P0 | **Provenance/audit trail per answer and action**: query, chunk IDs, page/bbox, model + version, prompt hash, reviewer, timestamp; exportable JSON/PDF | RAI, Product | Palantir "every action logged", lineage | "Show me why": a full trace for any output |
| 8 | P0 | **Markings + RBAC enforced in retrieval**: PII/PHI tags on chunks/fields, role-based redaction at query time, per-doc ACL filters in the vector index; agent sees only what the user may see | RAI, Product | Palantir role/marking/purpose-based security | Same question, two roles, two (correctly redacted) answers |
| 9 | P1 | **Cross-document consistency and contradiction detection** (invoice vs PO vs contract amounts; name/address mismatches; conflicting clauses across versions) | GenAI, ML | Tracer (notes vs labs); Palantir link analysis | Auto-flag "Amount on invoice ≠ contract cap" with both sources |
| 10 | P1 | **Playbook/regulation-grounded risk scoring**: compare clauses or fields against a policy playbook or regulation corpus; severity + suggested fallback language | GenAI, ML | ClinicDx/BridgeDx (guideline-grounded); PitchLense risk reports; Legal SahAI | A risk heat-map with one-click redline suggestions |
| 11 | P1 | **Document-strategy lab**: Tesseract-only vs VLM vs OCR-preprocessed VLM per doc type, auto-picked on measured quality/latency/cost | CV, ML | Palantir AIP Document Intelligence | Table: strategy × accuracy × seconds × $ |
| 12 | P1 | **Advanced CV extraction**: tables → structured rows, checkboxes, **signatures/stamps/handwriting detection**, chart-to-data | CV | Sixth Sense (detector → LLM); CodeBuddy (handwriting photos); UniRad3s; EdgeStyle | "Signed? Stamped? Initialled every page?" answered visually |
| 13 | P1 | **Tamper/forgery signals** for scans and IDs: error-level analysis, font/kerning inconsistency, copy-move, metadata anomalies, AI-generated image flags | CV, RAI | CopyFlag (AI-altered copies); Parallax; TrueVoice (Trust & Safety prize) | A forensic overlay on a doctored PDF |
| 14 | P1 | **Offline / air-gapped mode**: local VLM + LLM (Ollama / llama.cpp), local embeddings, no network egress; publish tokens/s and accuracy delta vs cloud | ML, RAI | Gemma 3n/4 winners; MedGemma Edge prize; Argus hybrid; NVIDIA RTX/Jetson contests | Wi-Fi off, still answers with citations |
| 15 | P1 | **Agentic deep-research memo** over the corpus: planner → retriever → critic → writer, producing a cited memo/brief | GenAI | Apollo (self-reflective RAG); ADK multi-agent winners; NVIDIA AI-Q blueprint (GTC 2026) | "Draft the due-diligence memo" → cited 2-page memo |
| 16 | P1 | **Obligation/timeline view**: all dates, deadlines, renewals across documents on one timeline + calendar export | Product, GenAI | Palantir operational apps; Medicall (time-critical) | "What's due in the next 30 days?" |
| 17 | P1 | **Entity resolution in the graph** (merge "ACME Pvt Ltd" / "Acme Private Limited"), with human-confirmable merges | ML | Palantir Ontology; Bit2Brain knowledge map | Clean graph instead of duplicate nodes |
| 18 | P2 | **Mobile capture with quality gating**: phone scan, blur/glare rejection (quality checks already exist), dewarp, multilingual and Indic OCR | CV, Product | Solution Challenge mobile-first winners; EpiCast/PreVillage local language; Sunny | Live "retake: too blurry" prompt, Hindi document answered in English |
| 19 | P2 | **Voice and multilingual Q&A** (ask in Hindi, answer with citations), accessible UI (screen-reader, high contrast) | GenAI, Product | Gemini Live Agent winners; accessibility champions (FROM YOUR EYES, Argus); Imagine Cup inclusive design | Inclusive-design checkbox for Microsoft/Google judges |
| 20 | P2 | **Active learning from reviewer corrections**: corrections become few-shot examples / fine-tune a small extractor (e.g., LayoutLM-family / Donut) with an accuracy-over-time chart | ML | Dream Assistant & Gem-Care (fine-tuned on real user data); Imagine Cup "continuous improvement" | "Accuracy rose from 81% → 93% after 200 corrections" |
| 21 | P2 | **Red-team suite + model card**: prompt-injection attack set (detector exists) with attack-success-rate metric, PII leakage tests, documented limitations | RAI | AI Trust & Safety prize (TrueVoice); Imagine Cup responsible-AI emphasis | A responsible-AI slide with measured numbers |
| 22 | P2 | **API + MCP server + webhooks** so other agents/apps can call MindDoc (extract, ask, act) | Product, GenAI | FROM YOUR EYES "app and API"; Palantir tools for agents; Bleach | "Any agent can use MindDoc as a tool" (platform story) |

**Fastest high-impact sequence (about 2–3 weeks of focused work):** 1 → 2 → 6 → 3 → 4 → 7 → 5 → 8, then pick 9/10/13 according to the chosen vertical.

---

## 8. Three candidate pitch positionings

### A. "AI paralegal for SMEs": contract and notice intelligence

- **User:** SME owner / in-house counsel / CA firm handling vendor contracts, leases, legal notices (India-first, English + Hindi).
- **Wedge:**
  - Upload contracts → obligation register.
  - Deadlines and renewals.
  - Risk vs a standard playbook.
  - Redline suggestions.
  - Bbox citations.
  - Lawyer-in-the-loop sign-off.
- **Core features:** #1, 2, 3, 4, 6, 9, 10, 16.
- **Judging angle:**
  - *Impact/usefulness:* "Contract review from hours to minutes", measured on CUAD clause extraction + time-on-task with 3–5 pilot users.
  - *Responsible AI:* abstention, citations, "not legal advice" with escalation to a lawyer.
  - *Business:* clear per-seat or per-document pricing.
- **Competitive note:** Legal SahAI already won Google's 2025 "Demystifying Legal Documents" track (RAG + form assistant + lawyer portal). Differentiate on **cross-document obligations graph, pixel-level provenance, governed actions, offline mode** and published accuracy.
- **Best fits:** Imagine Cup 2027 industry category, Google Cloud Gen AI Exchange-style tracks, LlamaIndex/LangChain contests.

### B. "Clinical-document copilot for under-resourced clinics"

- **User:** clinic staff / community health workers handling handwritten prescriptions, lab reports, discharge summaries and referral letters.
- **Wedge:**
  - Scans → structured patient timeline.
  - Medication reconciliation.
  - **Notes-vs-lab contradiction flags** (Tracer-style).
  - PHI markings.
  - **Fully offline** on a laptop.
  - Clinician sign-off.
- **Core features:** #1, 2, 3, 6, 8, 9, 12, 14, 18.
- **Judging angle:**
  - *Social impact + edge AI:* the exact profile of MedGemma/Gemma winners (EpiCast, FieldScreen, ClinicDx).
  - *Metrics:* field-level accuracy on synthetic records, errors caught, minutes saved per patient.
  - *Responsible AI:* decision support, not diagnosis; human authority; privacy by design.
- **Risks:** regulatory claims (stay "documentation support"); use **synthetic/public data only** (e.g., Synthea-generated records), not real patient data.
- **Best fits:** Kaggle/Google health and Gemma challenges, Solution Challenge, Imagine Cup health category, NVIDIA edge (Jetson/RTX) contests.

### C. "KYC / compliance document intelligence" (most Palantir-aligned)

- **User:** onboarding/compliance analysts at NBFCs, fintechs and banks processing IDs, bank statements, invoices, GST/incorporation certificates.
- **Wedge:**
  - Extraction → **cross-document consistency** (name/address/amount/date).
  - **Tamper detection**.
  - PII markings with role-based redaction.
  - Case objects in an ontology (Customer–Document–Account–Transaction).
  - Analyst **approve / reject / request-info** actions with a full audit trail.
- **Core features:** #1, 2, 3, 4, 7, 8, 9, 13, 17.
- **Judging angle:**
  - *Enterprise validation and investability* (Imagine Cup 2027 final-stage criteria).
  - *Measurable ROI:* analyst minutes per case, auto-clear rate, false-flag rate.
  - *Security, reliability and scalability* (explicitly scored).
  - *Palantir-style:* ontology + decisions + audit + access control.
- **Risks:** never use real IDs. Use synthetic ID datasets (e.g., MIDV-family) and generated statements. Avoid claiming regulatory certification.
- **Best fits:** Imagine Cup 2027 (startup categories), enterprise/fintech hackathons. This is also the strongest portfolio story for Palantir/defense-tech recruiters.

**Recommendation:**
- **C** for "impress Palantir / enterprise judges".
- **B** for Google/Kaggle social-impact and edge prizes.
- **A** as the broadest, easiest-to-pilot B2B story.

Keep one codebase with **switchable vertical schemas** (ontology packs), so the same engine can be pitched three ways.

---

## 9. Finals demo checklist (distilled from winners and judging rules)

1. **Persona and pain in 15 s**, with a real quote from a pilot user.
2. **Live upload of a messy scan** → quality check → structured objects appear in the graph/register.
3. **Ask one hard cross-document question** → answer with sentence-level support badges → click → highlighted region on the page.
4. **Agent proposes an action** → human approves → action executes (calendar/ticket/notice) → audit entry shown.
5. **Switch role** → the same query is redacted correctly.
6. **Wi-Fi off** → still works (offline mode).
7. **Metrics slide:** accuracy, faithfulness, latency, cost/doc, injection-attack success rate, pilot usage.
8. **Architecture slide** naming the sponsor's services, plus security/reliability/scalability notes; recorded backup video.

---

## 10. What could not be verified (caveats)

- **Imagine Cup 2026:** specific Azure services for CopyFlag/Revora/SpoilSafe and CopyFlag's traction numbers come from secondary/search sources. The 2026 judging-criteria wording comes from a Microsoft *staging* FAQ snippet. The 2027 criteria are from the FAQ (fetched via a staging-domain mirror in English).
- **Imagine Cup 2025:** Stanford Daily describes the other finalists as "from the U.S. and Rwanda", while Microsoft lists Signvrse as Kenya-focused (with African Leadership University, which has a Rwanda campus). Treat the country label as ambiguous.
- **Imagine Cup 2023:** the champion and finalist names come from i-programmer/Microsoft snippets, and the descriptions from Microsoft's 48-finalist page. The Microsoft "winner revealed" post itself was not fetched.
- **Google Solution Challenge 2025:** only Medicall (Top 3) and GeoGemma (Best AI Use Case, via Gulf News) are named. The other Top 3 teams and the People's Choice / Societal Impact winners are **not verified**. Whether a separate global 2025 edition existed beyond the APAC/ADB edition was not confirmed.
- **Gemini API Developer Competition:** developer names/countries and exact cash per category were not on Google's pages. Prize amounts and judging criteria are from secondary sources.
- **NVIDIA × LangChain:** CarePilot's "top three" claim conflicts with NVIDIA's winners page. Descriptions for AI Personal Trainer and Mystery Manor were not found.
- **NVIDIA × LlamaIndex:** the explicit ranks and ESG Insights AI's description are unclear (copy error on NVIDIA's page).
- **NVIDIA GTC 2025/2026 hackathons:** **no published winners found**. NVIDIA "Jetson AI" challenges for 2025/2026 were not found; the latest verified Jetson-centric contest is the 2024 Hackster/SparkFun challenge.
- **Microsoft AI Agents Hackathon:** monetary prize amounts are not shown on the official winners page (search snippets mention $20k for Best Overall [S]).
- **Palantir:** Bootcamp outcomes (conversion rates, Heineken example) are company-reported or third-party. Only the product principles are drawn from Palantir docs.
- **Dataset suggestions** (CUAD, FUNSD, SROIE, DocVQA, MIDV, Synthea) are standard public benchmarks suggested by the author. They were not part of the competition research.

---

## 11. Sources

**Microsoft**
- Imagine Cup winners history: https://imaginecup.microsoft.com/winners
- 2026 champion (Microsoft Signal): https://news.microsoft.com/signal/articles/imagine-cup-2026-student-ai-competition/
- 2026 finalists (Microsoft Bay Area blog): https://blogs.microsoft.com/bayarea/2026/05/29/meet-the-future-of-innovation-microsoft-imagine-cup-world-championship/
- 2026 finalists (MENA Startup Digest): https://menastartupdigest.com/microsoft-names-the-three-student-led-ai-startups-vying-for-the-2026-imagine-cup-title/
- 2026 world finalists (Tech Community): https://techcommunity.microsoft.com/blog/studentdeveloperblog/introducing-the-2026-imagine-cup-world-finalists/4509670
- 2026 semifinalists: https://techcommunity.microsoft.com/blog/studentdeveloperblog/ai-in-action-meet-the-2026-imagine-cup-semifinalists/4495567
- 2027 rules / FAQ (staging mirror): https://imaginecup-stg.microsoft.com/pl-pl/support/faq
- 2027 changes (GeekWire, via Slashdot): https://geekwire.com/2026/microsoft-opens-imagine-cup-to-startups-and-the-new-rules-show-how-its-ai-strategy-has-changed/ and https://tech.slashdot.org/story/26/11/05/057254/
- 2025 finalists and champion: https://news.microsoft.com/source/features/ai/students-aim-to-help-millions-with-ai-in-this-years-imagine-cup/
- 2025 champion announcement: https://techcommunity.microsoft.com/blog/studentdeveloperblog/announcing-the-2025-imagine-cup-world-champion/4414342
- Argus (Stanford Daily): https://stanforddaily.com/2025/06/05/juniors-ai-assistive-vision-device-takes-top-prize-at-microsoft-competition/
- 2024 top three: https://techcommunity.microsoft.com/blog/studentdeveloperblog/announcing-the-top-three-teams-of-the-2024-imagine-cup/4117733
- 2024 champion (Neowin): https://www.neowin.net/news/the-from-your-eyes-team-is-the-winner-of-microsofts-2024-imagine-cup-student-competition/
- 2024 judges post: https://techcommunity.microsoft.com/blog/studentdeveloperblog/introducing-the-2024-imagine-cup-world-championship-judges/4128464
- 2023 world finalists: https://techcommunity.microsoft.com/blog/studentdeveloperblog/meet-the-2023-imagine-cup-world-finalists/3754378
- 2023 winners (i-programmer): https://i-programmer.info/news/204-challenges/16331-imagine-cup-winners-2023.html
- 2023 winner revealed: https://techcommunity.microsoft.com/blog/studentdeveloperblog/2023-imagine-cup-world-championship-winner-revealed/3827602
- AI Agents Hackathon 2025 winners: https://microsoft.github.io/AI_Agents_Hackathon/winners/
- AI Agents Hackathon category showcase: https://techcommunity.microsoft.com/blog/azuredevcommunityblog/ai-agents-hackathon-2025-%E2%80%93-category-winners-showcase/4415088
- AI Classroom Hackathon winners: https://www.microsoft.com/en-us/education/blog/?p=5318
- Powerful Devs Hack Together 2025: https://devblogs.microsoft.com/powerplatform/announcing-the-winners-of-the-2025-powerful-devs-hack-together/

**Google**
- Gemini API Developer Competition winners: https://developers.googleblog.com/announcing-the-winners-of-the-gemini-api-developer-competition/
- Gemini API competition overview (Google blog): https://blog.google/innovation-and-ai/technology/developers-tools/gemini-api-developer-competition-winners/
- Gemini competition prizes (i-programmer): https://i-programmer.info/news/204-challenges/17193-google-gemini-api-developer-competition.html
- Gemini competition launch (VentureBeat): https://venturebeat.com/ai/win-the-worlds-fastest-delorean-in-googles-gemini-api-developer-contest
- Solution Challenge 2023 winners: https://blog.google/technology/developers/google-student-developer-clubs-solution-challenge-2023/
- Solution Challenge 2024 winners: https://blog.google/innovation-and-ai/technology/developers-tools/meet-the-students-that-are-changing-the-world-through-technology/
- Solution Challenge 2025, Atempo/Medicall: https://blog.google/intl/ko-kr/company-news/outreach-initiatives/2025-solution-challenge-atempo/
- Solution Challenge 2025, Guardy: https://blog.google/intl/ko-kr/company-news/outreach-initiatives/2025-solution-challenge-guardy/
- Solution Challenge 2025, GeoGemma (Gulf News): https://gulfnews.com/world/asia/pakistan/pakistani-students-win-big-at-google-solution-challenge-2025-1.500184786
- Solution Challenge 2025 event (ADB): https://events.eventboost.com/nfe/adb-asia-pacific-digital-transformation-forum-2025/42897/google-solutions-challenge/en_US
- Gemma 3n Impact Challenge winners: https://blog.google/technology/developers/developers-changing-lives-with-gemma-3n/
- MedGemma Impact Challenge winners: https://blog.google/innovation-and-ai/technology/health/med-gemma-impact-challenge/
- Gemma 4 Good Challenge winners: https://blog.google/innovation-and-ai/technology/developers-tools/winning-entries-gemma-4-good-challenge/
- ADK Hackathon results: https://cloud.google.com/blog/products/ai-machine-learning/adk-hackathon-results-winners-and-highlights
- Gemini Live Agent Challenge winners: https://cloud.google.com/blog/topics/developers-practitioners/winners-and-highlights-of-the-gemini-live-agent-challenge
- Gen AI Exchange Hackathon finale (Hack2skill): https://blog.hack2skill.com/gen-ai-exchange-hackathon-finale
- Gen AI Exchange Hackathon (Outlook Business): https://www.outlookbusiness.com/deeptech/artificial-intelligence/google-cloud-gen-ai-hackathon-2025-winners-use-cases-and-what-270000-developers-built

**NVIDIA**
- NVIDIA × LangChain Agents Contest (winners listed on main page): https://www.nvidia.com/en-us/ai-data-science/generative-ai/developer-contest-with-langchain/
- NVIDIA × LangChain contest terms: https://www.nvidia.com/en-us/ai-data-science/generative-ai/developer-contest-with-langchain/terms-and-conditions/
- Agents of Inference (Brian Caffey): https://briancaffey.github.io/2024/06/17/agents-of-inference-nvidia-and-langchain-generative-ai-agent-developer-contest
- CarePilot claim (UW-Milwaukee): https://sites.uwm.edu/jakeluo/?p=416
- NVIDIA × LlamaIndex Developer Contest: https://developer.nvidia.com/llamaindex-developer-contest
- LlamaIndex contest winner forum thread: https://forums.developer.nvidia.com/t/winner-nvidia-and-llamaindex-developers-2024/317943
- Gen AI on RTX PCs winners: https://www.nvidia.com/en-us/ai-data-science/generative-ai/rtx-developer-contest/winners
- Agent Toolkit Hackathon: https://developer.nvidia.com/agentiq-hackathon
- Agent Toolkit Hackathon winners blog: https://developer.nvidia.com/blog/hackathon-winners-bring-agentic-ai-to-life-with-the-nvidia-nemo-agent-toolkit/
- Hackster/SparkFun AI Innovation Challenge winners: https://blogs.nvidia.com/blog/glados-robot-hackster
- Cosmos Cookoff winners: https://forums.developer.nvidia.com/t/the-results-are-in-meet-the-nvidia-cosmos-cookoff-winners-see-them-live-on-april-16/366130
- GTC hackathons: https://developer.nvidia.com/gtc-hackathon.md

**Palantir**
- Ontology overview: https://www.palantir.com/docs/foundry/ontology/overview/
- AIP overview: https://www.palantir.com/docs/foundry/aip/overview/
- AIP security: https://www.palantir.com/docs/foundry/aip/aip-security/
- AIP architecture: https://palantir.com/docs/foundry/architecture-center/aip-architecture
- Foundry platform summary: https://palantir.com/docs/foundry/getting-started/foundry-platform-summary-llm/
- AIP Document Intelligence overview: https://palantir.com/docs/foundry/document-intelligence/overview/
- AIP Document Intelligence core concepts: https://palantir.com/docs/foundry/document-intelligence/core-concepts/
- AIP Bootcamps (Constellation Research): https://www.constellationr.com/blog-news/insights/palantirs-commercial-business-scales-help-ai-boot-camps
- AIP Bootcamps (Motley Fool): https://www.fool.com/investing/2024/05/16/this-is-palantirs-ai-growth-secret-weapon
