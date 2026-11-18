# CloudFide — Autonomous Data Engineering Delivery

**Status:** plan docelowy; NIE oznacza wdrożonego systemu autonomicznego.  
**Repozytorium:** `maciejbrasewicz/cloudfide-agentic-data-engineering`  
**Data odniesienia:** 2026-11-18  
**Zasada:** trzy role LLM, jeden deterministyczny orchestrator, osobne i niezależne bramki wykonawcze.

## 0. Cel, rezultat i granice

Budujemy **autonomiczny, ale kontrolowany proces dostarczenia dokładnie tego samego zadania CloudFide**, a nie kolejną aplikację i nie trzeci system do raportowania. Wejście: oryginalna specyfikacja zadania (przekazywana prywatnie w runtime), oryginalny `sales.csv` i `test_virtual_column.py`, opcjonalnie zatwierdzona polityka biznesowa. Wyjście: faktycznie wygenerowane i przetestowane `solution.py`, `pipeline.py`, `revenue_by_region.csv`, własne testy i `README.md`, raport weryfikacji, historia iteracji i **draft PR**.

Nie wolno publikować treści oryginalnej specyfikacji w repozytorium. Oryginalne pliki wejściowe oraz testy firmy pozostają identyczne bajtowo. `pipeline.py` pozostaje deterministyczny — do obliczeń nie wywołuje modelu. Akceptacja zmian polityki biznesowej i merge zawsze należą do człowieka.

### Dwa tryby wykonania

| Tryb | Dostęp agenta do istniejącego rozwiązania | Cel |
|---|---|---|
| `rebuild` (docelowy pokaz) | **Brak** dostępu do aktualnego `solution.py`, `pipeline.py`, prywatnego oracle i gotowego CSV; tylko oryginalne wejście, specyfikacja, zatwierdzone reguły i jawne API narzędzi | **Udowodnić**, że agenci potrafią wytworzyć całe rozwiązanie od początku |
| `improve` | Tylko określone pliki w istniejącym projekcie, wyniki CI, zgłoszone błędy i dozwolone repozytoryjne źródła | Wykazać iteracyjne naprawianie rzeczywistych defektów |

Uwaga: publiczne repozytorium sprawia, że nie istnieje absolutny dowód „model nigdy nie widział rozwiązania”. W `rebuild` nie udostępniamy go **przez nasze narzędzia ani workspace**; dowodem procesu są wygenerowane kandydackie pliki, ślady narzędzi i niezależne wykonania. Nie przedstawiamy tego jako kryptograficznego dowodu oryginalności autorstwa.

### Bezwzględne warunki akceptacji

1. **Architekt wytwarza kontrakt i decyzje** na podstawie rzeczywistej specyfikacji i źródła, z policzonymi dowodami.
2. **Engineer zapisuje prawdziwy kod**, testy i dokumentację do izolowanego workspace; sama odpowiedź tekstowa to porażka.
3. **Verifier tworzy własne testy falsyfikacyjne**, które są uruchamiane bezpośrednio na wygenerowanej kandydaturze; sam komentarz nie wystarcza.
4. **Pętla działa**: reprodukowalny błąd -> raport -> poprawka Engineera -> niezależny ponowny test; maks. 3 iteracje.
5. **Deterministyczne bramki rozstrzygają**; trzy poprawne JSON-y nie mogą ustawić `PASS`.
6. **Jeden przycisk** GitHub Actions uruchamia cały proces, a rezultat jest powiązany z konkretnym `run_id`, SHA i artefaktami; panel web jest dodatkiem po weryfikacji.
7. **Brak samozatwierdzania** przez LLM: niezmieniona polityka zatwierdzona, zmiany polityki `AWAITING_HUMAN_APPROVAL`, draft PR do ludzkiego przeglądu.

## 1. Faktyczny stan początkowy (zastany, nie docelowy)

- `solution.py`, `pipeline.py`, niezależny oracle, Pydantic/Pandera, pytest/Hypothesis oraz kontrola wyników już działają.
- `agentic/run.py` tworzy tylko 3 **recenzentów read-only** przez `SequentialBuilder`; obecny Data Engineer nie tworzy kodu, Verification Engineer nie zapewnia automatycznej iteracji naprawczej.
- Workflow `.github/workflows/agent-review.yml` **nie przekazuje `--task-file`**, więc model nie czyta pełnej pierwotnej specyfikacji w tych uruchomieniach.
- Zrealizowany audyt `44379368776` zwrócił 3 raporty, 17 zarejestrowanych wywołań narzędzi, 9 propozycji decyzji; raport Engineera nie wykazał skutecznej weryfikacji implementacji. Walidacja obecnego manifestu potwierdza zgodność artefaktów, a nie jakość wszystkich działań ról.
- `.github/workflows/agent-coding-proposal.yml` umożliwia propozycję **jednego testu regresyjnego**; nie jest to budowa programu ani pętla naprawcza, a pełne produkcyjne wykonanie tego workflow nie zostało potwierdzone.
- `showcase/` jest **jednym** serwisem i pozostanie nim. Dane szczegółowe na stronie wciąż pochodzą z udokumentowanego przebiegu historycznego, nie z automatycznie aktualizowanej listy wszystkich przebiegów.

**Zasada migracji:** istniejący `agent-review.yml` i działający ETL zachowujemy jako baseline/legacy, dopóki nowy workflow nie przejdzie wszystkich testów. Nowy proces ma osobną nazwę `agent-delivery.yml`; nie podmieniamy działającego audytu w ciemno.

## 2. Architektura docelowa — kontroler i ścisłe role

```text
  INPUT: zadanie (runtime only) + sales.csv + test_virtual_column.py
                            |
                  [INPUT INTEGRITY / SHA]
                            |
                  [DATA ARCHITECT / Foundry]
                profil + kontrakt + uzasadnienia
                            |
                    [POLICY APPROVAL GATE]
        stara zatwierdzona polityka / STOP na zmianę niezatwierdzoną
                            |
                  [DATA ENGINEER / Foundry]
                   realne pliki / patch / tests
                            |
            [ISOLATED RUNNER / no secrets, no network]
               lint + pytest + oracle + artifacts
                            |
              [VERIFICATION ENGINEER / Foundry]
             niezależna inspekcja + nowy kontrprzykład
                            |
            [INDEPENDENT ADVERSARIAL TEST RUNNER]
                            |
               [DETERMINISTIC CONTROLLER / gates]
                 | PASS              | REWORK         | STOP
                 v                   |                v
            [DRAFT PR] <-------------+         [REJECTED/HUMAN]
           + evidence    (do 3 iteracji)
```

**Orchestrator to kod, nie czwarty agent.** Mamy trzy agenty LLM. Kod odpowiada za stan, przejścia, licznik iteracji, obowiązkowe wywołania narzędzi i dowody. `SequentialBuilder` pozostaje właściwy dla prostego, liniowego audytu, ale do warunkowego przełączania ról, retry i punktu zatwierdzenia użyjemy **jawnej maszyny stanów / `WorkflowBuilder`**, zgodnie z wersją zainstalowanego Microsoft Agent Framework. Wsparcie checkpointów i HITL wymaga własnych testów integracyjnych na przypiętym SDK, a nie założenia, że pojedyncza sekwencja obsługuje cały proces.

### Agent 01 — Data Architect

**Dostaje:** dokładną specyfikację, oryginalne CSV, oryginalne testy, profil źródła i dopuszczalną listę reguł; w `rebuild` nie widzi implementacji.  
**Narzędzia:** `read_spec`, `inspect_original_tests`, `profile_source`, `inspect_orders`, `reconcile_raw_control`, `validate_policy_proposal`. Każdy tool zwraca dowód z identyfikatorem, liczbami i SHA źródła, nie dowolny tekst.  
**Zapisuje:** `architect_report.json` i `contract_proposal.json` (schemat pól, reguły, ograniczenia, niejednoznaczności, testy akceptacyjne, odwołania do dowodów).  
**Obowiązkowe wyniki:** wszystkie 3 części specyfikacji CloudFide ujęte w kontrakcie; dowód na 1507 fizycznych wierszy, 1505 surowych transakcji, 1 powtórzony nagłówek, 1 TOTAL, 5 dodatkowych duplikatów; rozdzielenie kontroli `TOTAL` przed deduplikacją od kontroli po deduplikacji; odróżnienie jawnej reguły pustego rabatu od założeń o zwrotach i cenach.  
**PASS:** odpowiedź zgodna ze schematem, wszystkie obowiązkowe narzędzia faktycznie wywołane, przynajmniej jeden dowód na każdą istotną regułę, zgodność policzonych faktów z niezależnym profilerem; brak niezatwierdzonej zmiany polityki.

### Agent 02 — Data Engineer

**Dostaje:** specyfikację, zatwierdzony kontrakt i decyzje Architekta, oryginalne wejścia, wcześniejsze błędy z runnera/verifiera; w `improve` również aktualny dozwolony kod. Nie otrzymuje ukrytych testów weryfikacyjnych.  
**Narzędzia:** `list_workspace`, `read_workspace_file`, `write_candidate_file`, `show_diff`, `request_validation` (ostatnie wyłącznie zleca sandbox, nie wykonuje modelowego kodu z tokenami chmurowymi). GitHub MCP w `improve` do odczytu historii/review; w `rebuild` wyłączone do czasu utworzenia oryginalnej kandydatury.  
**Zakres plików:** `solution.py`, `pipeline.py`, `README.md`, własne `tests/test_*.py` i, po zatwierdzeniu, `contracts/data_policy.json`; pliki źródłowe/test firmy są read-only. Żadnych zmian workflow, zależności, sekretów ani skryptów wdrożeniowych przez model.  
**Zapisuje:** prawdziwe pliki w *izolowanym kandydackim workspace*, `engineer_change_manifest.json`, diff, uzasadnienie i mapowanie requirements -> test. `revenue_by_region.csv` musi powstać **przez uruchomienie wygenerowanego `pipeline.py` w sandboxie**, nie być skopiowaną odpowiedzią LLM.  
**PASS:** istnieją i są zmienione wymagane artefakty (w `rebuild` powstały od zera); czytelny diff i ślad `write_candidate_file`; brak niedozwolonych modyfikacji; wszystkie testy i porównanie wyniku po wykonaniu kandydata przechodzą.

### Agent 03 — Verification Engineer

**Dostaje:** dokładną specyfikację, dane źródłowe, zatwierdzony kontrakt, *rzeczywisty* kod kandydata, raport runnera, wyniki niezależnego oracle; **nie polega na akceptacji Engineera**.  
**Narzędzia:** `read_candidate_file`, `inspect_reconciliation`, `inspect_validation_receipt`, `inspect_original_tests`, `propose_adversarial_test`, `request_independent_validation`; brak uprawnień do edycji kodu produkcyjnego.  
**Zapisuje:** `verifier_report.json`, minimum jeden rzeczywisty dodatkowy test `tests/verifier_generated_*.py` jako **odrębny artefakt**, falsyfikowalny werdykt i ewentualny `rework_request.json` z dowodem błędu.  
**PASS:** wszystkie obowiązkowe interfejsy wykonane, test zweryfikowany w osobnym runnerze, opinia powiązana z wynikami, brak nierozwiązanych defektów high, niezależne źródło dowodu dla kluczowych wartości.

**Hard gate ról:** wynik JSON to dopiero składnia. Brak obowiązkowego `tool_call` przypisanego do właściwego `agent_role`, brak wygenerowanego pliku lub brak wykonywalnego dowodu => `INCOMPLETE` / `FAIL`. Telemetria musi trwale wiązać wywołanie z agentem, iteracją, czasem i wynikiem. Jeśli SDK nie dostarczy tego automatycznie, przypisanie tworzy kontrolowany wrapper narzędzi na granicy danego agenta i testujemy to osobno.

## 3. Sterownik, stany, powroty i decyzje

Dozwolone stany: `CREATED`, `INPUT_VERIFIED`, `ARCHITECT_COMPLETE`, `AWAITING_HUMAN_APPROVAL`, `POLICY_APPROVED`, `ENGINEERING`, `CANDIDATE_READY`, `VALIDATING`, `VALIDATION_FAILED`, `VERIFYING`, `VERIFICATION_FAILED`, `REWORK`, `ACCEPTED`, `DRAFT_PR_CREATED`, `REJECTED`, `INFRA_FAILURE`.

Maszyna stanów ma jedno źródło prawdy: `run_state.json` zapisane atomowo i podpisane hashami artefaktów. Każda zmiana stanu wymaga zdarzenia `gate_receipt` z wejściami, wyjściami i powodem; brak danych => stop. Domyślnie maks. 3 próby kodu; retry po potwierdzonym błędzie daje Engineerowi **konkretny failing test i stack trace**, a nie wolnotekstową prośbę o „poprawę”. Identyczne patche, pusta zmiana, utrata zgodności źródeł i wyczerpanie limitu => `REJECTED` z diagnozą. Błąd infrastruktury nie jest traktowany jako defekt kodu i nie generuje fałszywej poprawki.

`ACCEPTED` dopuszczalne **tylko**, gdy: przyjęty kontrakt polityki, poprawne pliki i diff, testy oryginalne i własne, ścisła kontrola źródła i wyniku, test Verifiera, brak blokujących ustaleń, poprawne SHA, kompletna telemetria ról. Po `ACCEPTED` oddzielny proces wystawia roboczy PR. PR nie jest automatycznie scalany.

**Human gate:** obecna `contracts/data_policy.json` v1 jest zatwierdzonym *punktem odniesienia dla demonstracji*, nie dowodem prawdziwości semantyki biznesowej. Nowa propozycja zmiany reguł (usuwanie duplikatów, interpretacja zwrotów, imputacja ceny itp.) nie może być automatycznie zastosowana — zatrzymujemy proces do zatwierdzenia. Przebieg z istniejącą zatwierdzoną polityką powinien działać jednym kliknięciem bez oczekiwania na dialog.

## 4. Odseparowane wykonywanie wygenerowanego kodu

Obecny workflow coding-proposal uruchamia modelowy test na osobnym jobie, ale docelowo musimy hardenować izolację: **żaden niezweryfikowany kod wygenerowany przez LLM nie może wykonać się w jobie z dostępem do Azure OIDC, sekretów, uprawnień zapisu do repo czy tokenu dostępu do Foundry**.

Implementacja dla GitHub Actions:

- **Zaufane joby `architect`, `engineer`, `verifier`:** `contents: read`, `id-token: write` tylko dla ograniczonej tożsamości Foundry; nie wykonują żadnego kodu kandydata; nie pokazują specyfikacji w logach i nie publikują jej w artifactach.
- **Niezaufane joby `candidate-tests`, `adversarial-tests`:** bez sekretów i bez Azure, z minimalnymi uprawnieniami; zależności instalowane z zaufanego, przypiętego lockfile *przed* dodaniem kodu kandydata; generowany kod wykonuje się w odizolowanym kontenerze z `--network none`, `--read-only`, `--cap-drop ALL`, `--security-opt no-new-privileges`, ograniczeniami pamięci/procesów/czasu, bez hostowego Docker socket i bez hostowych ścieżek poświadczeń. Workspace kandydata jako read-only, osobne ograniczone `/tmp` i `/results`.
- **Publikowanie `draft PR`:** oddzielny job posiadający uprawnienia `contents: write`, `pull-requests: write` i **bez OIDC/sekretów Foundry**, który pobiera *tylko* zatwierdzone manifestem pliki i weryfikuje ich hash oraz ścieżki. Dopiero wtedy tworzy branch/PR.
- Testy bezpieczeństwa przed wdrożeniem: kontrolowany złośliwy kandydat próbujący odczytać env, sieć, pliki spoza workspace, wykonać shell i nadpisać `sales.csv` musi zostać odrzucony lub uruchomiony bez skutków. Nie zakładamy skuteczności izolacji bez tych testów.

**Pułapka GitHub:** operacje z użyciem domyślnego `GITHUB_TOKEN` nie wywołują zwykle kolejnego `push`/`pull_request` workflow. Dlatego po utworzeniu PR musimy jawnie wywołać `workflow_dispatch` CI dla dokładnego SHA/brancha (dodać go do `ci.yml`) albo użyć zatwierdzonego GitHub App installation token. Werdykt końcowy musi wskazywać rzeczywiste zielone CI dla właściwego commita, nie „PR created”.

## 5. Oryginalna specyfikacja i kontrola wejścia

Oryginalne instrukcje CloudFide **nie mogą trafić do Git**. Jednorazowa konfiguracja: repozytoryjny/environment secret `CLOUDFIDE_TASK_SPEC_B64` ustawiony z oryginalnego `taskvirtualcolumn.md` (Base64 służy do transportu; poufność zapewnia GitHub Secret). W jobach wymagających specyfikacji zapisujemy ją wyłącznie do tymczasowego pliku poza checkoutem; brak `set -x`, brak `cat` do logów, usuwanie po odczycie. Alternatywą w kolejnej iteracji jest Azure Key Vault przez OIDC, ale nie warunkujemy od niego MVP.

`input_manifest.json` dokumentuje: SHA-256 oryginalnego `sales.csv`, `test_virtual_column.py`, specyfikacji, zatwierdzonej polityki, commit base, deployment modelu, wersje bibliotek, tryb i run-id. Nie zawiera pełnego tekstu zadania. W `rebuild` ładowany jest tylko oryginalny zestaw wejściowy; pliki z `main` (`solution.py`, `pipeline.py`, `revenue_by_region.csv`, rozwiązania w `tests/`) są niedostępne w tym workspace. Ukryty oracle i wyniki oczekiwane pozostają wyłącznie w niezależnym evaluatorze.

## 6. Kontrakty i artefakty — minimalne API między etapami

| Artefakt | Producent | Użycie / kontrola |
|---|---|---|
| `input_manifest.json` | Input controller | SHA źródła, testów, specyfikacji, repozytorium |
| `architect_report.json` + `contract_proposal.json` | Architect | Reguły, dowody, niepewności, kontrakt i decyzje |
| `approved_policy_receipt.json` | Deterministyczna bramka | Hash zatwierdzonej polityki; każda zmiana wymaga zgody |
| `engineer_change_manifest.json` + kandydackie pliki | Engineer | Ścieżki allowlist, SHA, diff, opis wymagania -> implementacja |
| `validation_receipt.json` | Isolated runner | Ruff, pytest, oryginalne testy, Pandera, niezależny oracle, exit codes |
| `verifier_report.json` + `verifier_generated_test.py` | Verifier | Kontrprzykład i wynik osobnego wykonania |
| `run_state.json` + `iteration_history.json` | Controller | Stany i powody decyzji per iteracja |
| `execution_trace.json` | Instrumentacja | Role, tool calls, czas, status, SHA, model, tokeny gdy dostępne |
| `acceptance_manifest.json` + `evidence_report.md` | Gate | Jednoznaczny wynik i odnośniki do pochodzenia każdego dowodu |
| `draft PR` | Publisher | Kod, testy, CSV, README, CI, dowody, link do audytu |

Modele Pydantic muszą stosować `extra=forbid`, dokładne wersje schematów, `Literal` dla stanów i kategorii, `sha256` dla danych i kodu, bounded counts i wymogi jakościowe. Zapis JSON musi być atomowy. **Model nigdy nie zwraca `approved=true` jako źródła prawdy**. Kontroler przypisuje status na podstawie faktów z runnera i zatwierdzeń.

## 7. Wymagania testowe dla zadania CloudFide

**Funkcja (`solution.py`):** `add_virtual_column(df, role, new_column)`, tylko nazwy literowe/underscore, wyrażenia `+ - *`, nieważna kolumna/wyrażenie -> pusty DataFrame, nowy obiekt i brak modyfikacji wejścia, bez `eval/exec` i bez arbitralnych wywołań. Oryginalne testy muszą przejść bez zmian.

**Pipeline (`pipeline.py`):** ładuje CSV, naprawia znane problemy tylko według zatwierdzonej polityki, liczy `quantity * unit_price - discount`, agreguje 5 regionów i generuje `revenue_by_region.csv`. `sales.csv` 1507 wierszy, surowe 1505 pozycji, 1 header, 1 TOTAL, 5 nadmiarowych identycznych pozycji, 1500 po deduplikacji. Kontrole oryginalnego `TOTAL`: 37150 ilości i 65924.67 rabatów **przed** usuwaniem duplikatów. Suma końcowa wg v1: **2570247.03**; regiony: Central 515824.67, East 442219.91, North 665897.52, South 504036.04, West 442268.89. Żadnego cichego „naprawiania” nieznanych anomalii.

**Niezależność:** osobny oracle z `csv` + `Decimal`, który nie importuje `solution.py`/`pipeline.py`, porównanie bajtów oryginalnych wejść, test ścieżek/niejednoznacznych cen/ujemnych ilości, deterministyczny regres po ponownym uruchomieniu, fault injection: celowo błędny rabat, pominięta deduplikacja, zła normalizacja, fałszywy TOTAL — testy muszą wykrywać. Verifier musi dołożyć nowy kontrprzykład i potwierdzić jego wykonanie.

**Provenance:** źródło, polityka, specyfikacja (tylko hash), candidate, testy i wynik spięte w jeden `run_id + SHA`. Blokująca rozbieżność = `FAIL`. Jeżeli semantyka duplikatów, zwrotów lub cen pozostaje niepotwierdzona u właściciela źródła, raport wyraźnie mówi „założenie w ramach polityki v1”; testy nie udowadniają historii handlowej.

## 8. GitHub Actions i interfejs operatora

**Nowy główny przycisk:** `Actions → Agentic Data Engineering — full delivery → Run workflow` (`.github/workflows/agent-delivery.yml`), gałąź `main`, parametry `mode: rebuild|improve`, `max_rounds: 1..3`, `publish_draft_pr: true|false`. Workflow uruchamia zadanie jednocześnie tylko na jednym kontrolowanym środowisku, ma limity kosztu/iteracji i wymagany manualny trigger (nie wykonuje generowanego kodu z dowolnego zewnętrznego PR).

Schemat jobów logicznych:

`bootstrap → architect → policy_gate → engineer_r1 → sandbox_r1 → verifier_r1 → adversarial_r1 → decision_r1 → [engineer_r2 → ...] → final_gate → publish_pr → ci_on_candidate`.

W GitHub Actions zależności w grafie jobów są statyczne: implementacja ma jawnie zakodowane maks. trzy rundy z warunkami `if:` i przekazaniem artefaktów. Nie projektujemy nieskończonej, niemożliwej do audytu rekurencji. Controller zbiera wyniki z każdej rundy i publikuje końcowy raport nawet przy `REJECTED` / `INFRA_FAILURE`.

**Przycisk na portalu:** po pozytywnym E2E aktualizujemy istniejący `showcase/` (jeden serwis), aby pokazywał wybór realnego `run_id`, aktualną rolę/iterację, fail/pass i artefakty. Wymaga minimalnego chronionego API i operatorowego tokenu na Railway; dopóki nie jest skonfigurowany, odsyłamy do GitHub Actions. Bez fałszywej animacji czy raportów sprzed zmian udających najnowszy przebieg.

## 9. Etapy implementacji, konkretne pliki i Definition of Done

### P0 — wejście, baseline i specyfikacja

- **Nowe:** `agentic/spec_loader.py`, `agentic/input_manifest.py`, `agentic/schemas/requirements.py`, `tests/test_spec_loader.py`.
- Utworzyć bezpieczny mechanizm przekazywania specyfikacji i hash, zestaw wejścia `rebuild`, test oryginalnego CSV/testów, selekcję trybu.
- **DoD:** brak specyfikacji => FAIL; modyfikacja fixture => FAIL; w `rebuild` Engineer nie może przez żadne narzędzie odczytać istniejącej implementacji.

### P1 — realny Architect i bramka polityki

- **Nowe:** `agentic/architect.py`, `agentic/source_tools.py`, `agentic/policy_gate.py`, `agentic/schemas/architect.py`, `tests/test_architect_contract.py`.
- Pydantic kontrakt, obowiązkowe tool calls, ewidencja faktów i założeń, zapisywalne propozycje decyzji, porównanie v1 bez automatycznej akceptacji zmian.
- **DoD:** Architect faktycznie rozpoznaje anomalie i umie wskazać dowody; brak wymaganej inspekcji/fakt niezgodny z profilerem => FAIL; niezatwierdzona zmiana => AWAITING_HUMAN_APPROVAL.

### P2 — prawdziwy Engineer i artefakty kodu

- **Nowe:** `agentic/engineer.py`, `agentic/workspace.py`, `agentic/patch_policy.py`, `agentic/schemas/engineer.py`, `tests/test_workspace_security.py`.
- Izolowany workspace, allowlist plików, atomowe zapisy, diff i SHA, autentyczny zapis Pythona/testów/README, ścisłe oddzielenie mode=`rebuild` od `improve`.
- **DoD:** `rebuild` produkuje kod z gołego zadania; patch poza allowlist, symlink traversal, próba zmiany fixture => FAIL; pusty JSON raport bez plików => FAIL.

### P3 — niezależny wykonawca i testy

- **Nowe:** `agentic/validation_runner.py`, `scripts/validate_candidate.py`, `docker/validation.Dockerfile`, `agentic/schemas/validation.py`, `tests/test_validation_isolation.py`.
- Kontener bez sieci/sekretów, uruchomienie kandydata i własnych testów, oryginalnych testów, kontrola wyników, niezależny oracle, maszynowy `validation_receipt.json`.
- **DoD:** realny poprawny kandydat PASS; znane mutacje i próby wyjścia z izolacji FAIL; żaden modelowy kod nie działa w jobie Foundry.

### P4 — niezależny Verifier

- **Nowe:** `agentic/verifier.py`, `agentic/adversarial_test.py`, `agentic/schemas/verifier.py`, `tests/test_verifier_evidence.py`.
- Verifier czyta kod i receipts, proponuje co najmniej jeden rzeczywisty sprawdzalny kontrprzykład/test, który wykonuje oddzielny runner; raportowane ustalenia mają reproduktory.
- **DoD:** brak wykonanego testu Verifiera => INCOMPLETE, zmyślone dowody i fałszywe przypisania narzędzi => FAIL; zmiana kodu przez Verifiera => FAIL.

### P5 — kontroler, bounded retry i checkpointy

- **Nowe:** `agentic/orchestrator.py`, `agentic/state_machine.py`, `agentic/evidence.py`, `agentic/role_telemetry.py`, `tests/test_orchestrator_transitions.py`.
- Jawne przejścia, 1..3 iteracje, resume/stop, restart bez powtarzania zatwierdzeń, agregacja receipts, klasyfikacja INFRA vs CODE, przypisane rolom tool events.
- **DoD:** zasiany defekt uruchamia rework i kończy się poprawką lub REJECTED po limicie; nie ma ścieżki PASS przez samą deklarację LLM; awaria infrastruktury nie jest oceną kodu.

### P6 — pełny workflow i PR

- **Nowe:** `.github/workflows/agent-delivery.yml`, `scripts/publish_candidate_pr.py`, `tests/test_delivery_workflow_contract.py`.
- Manualny `workflow_dispatch`, OIDC dla ograniczonych jobów, osobne no-secret test jobs i publikacja, hash/diff/branch/provenance, wymuszenie testu CI na SHA kandydata.
- **DoD:** jeden przycisk wywołuje całą sekwencję, prawdziwe pliki i nowy draft PR; zielone CI na kandydackim SHA, brak automerge. W przypadku FAIL powstaje raport, nie „sukces”.

### P7 — portal i demonstracja dla rekrutera

- **Zmiany:** istniejący `showcase/` i jego testy; bez drugiej aplikacji.
- Pokazać problem, wejście, samodzielnie wygenerowany kod, dowody testów, realne wyniki, iteracje i PR. Live status tylko z podpisanych zdarzeń; rozróżnienie runtime historycznego i aktualnego.
- **DoD:** rekruter jednym linkiem widzi pojedynczy konkretny przebieg end-to-end i może otworzyć odtworzenie, źródła, testy i PR; języki PL/EN, desktop/mobile bez regresji.

## 10. Scenariusze akceptacyjne E2E (obowiązkowe przed uznaniem za ukończone)

| ID | Scenariusz | Oczekiwany stan |
|---|---|---|
| E2E-01 | `rebuild` z samym oryginalnym zadaniem i fixture | Agent tworzy od zera wymagany kod, testy, README i wygenerowany wynik; wszystkie deterministic checks przechodzą |
| E2E-02 | Zasiana błędna formuła rabatu w kandydaturze | Sandbox/Verifier pokazuje konkretny failing test; Engineer poprawia; drugi przebieg przechodzi |
| E2E-03 | Agent Engineer nie czyta wymaganych plików lub zwraca tylko JSON | `INCOMPLETE`, brak fałszywego PASS |
| E2E-04 | Verifier nie uruchomił własnego testu | `INCOMPLETE`, brak draft PR |
| E2E-05 | Niejasna nowa propozycja biznesowej zmiany deduplikacji | `AWAITING_HUMAN_APPROVAL`; brak automatycznej zmiany `data_policy.json` |
| E2E-06 | Generated code próbuje odczytać token, wyjść do sieci, nadpisać oryginalny CSV | Test izolacji FAIL, źródło i tajne wartości niezmienione |
| E2E-07 | Błąd Foundry, MCP, przerwa w połączeniu | `INFRA_FAILURE`, nie `FAILED_CODE`; brak nieuzasadnionego PR |
| E2E-08 | Trzecia iteracja wciąż nie przechodzi | `REJECTED` z reproduktorem, hashami i historią |
| E2E-09 | Sukces -> draft PR | Tylko dozwolone pliki, SHA, zielone realne CI dla kandydata, audytowalny report |
| E2E-10 | Jeden klik z GitHub Actions | End-to-end bez lokalnych narzędzi i bez ręcznego `az login` |

## 11. Czego **nie** robimy

- Nie tworzymy czwartego agenta LLM, dodatkowej aplikacji rekrutacyjnej ani odrębnego portalu dla technicznej prezentacji.
- Nie używamy Fabric/Databricks do 1500 wierszy; obliczenia pozostają deterministyczne.
- Nie pozwalamy AI swobodnie uruchamiać komend shell, zmieniać zależności, workflow, sekretów, polityki biznesowej ani kodu na `main`.
- Nie ogłaszamy 100% poprawności semantycznej danych bez właściciela źródła; matematyczna zgodność i wiedza biznesowa to inne dowody.
- Nie budujemy panelu zanim full-delivery workflow nie przejdzie E2E-01 do E2E-10.

## 12. Kolejność realizacji i punkt wejścia do prac

Zaczynamy od **P0 i P1**, bez ingerencji w istniejący pipeline. Przed przejściem do P2: aktualny manifest, prywatna specyfikacja przekazywana w GitHub Actions, działający profiler z testami i prawdziwy raport Architect. Następnie wdrażamy pisanie kodu, izolowane uruchamianie, testy Verifiera, kontroler iteracji, publikację draft PR i na końcu web.

**Definicja sukcesu całego projektu:** realne wykonanie E2E-01 oraz E2E-02 z niezależnymi artefaktami i możliwością odtworzenia jednym przyciskiem; brak błędów E2E-03..E2E-10; repozytorium CloudFide zawiera poprawne wymagane pliki, a nowe rozwiązanie jest dostępne jako draft PR po zweryfikowanym przebiegu. Do tego momentu w materiałach określamy implementację jako `in progress`, nie `autonomous delivery complete`.

## Materiały techniczne do weryfikacji podczas implementacji

- Microsoft Agent Framework: `WorkflowBuilder` i wykonanie https://learn.microsoft.com/en-us/agent-framework/concepts/workflows/builder-and-execution?pivots=programming-language-python
- Microsoft Agent Framework: human-in-the-loop https://learn.microsoft.com/en-us/agent-framework/workflows/human-in-the-loop
- Microsoft Agent Framework: checkpoints https://learn.microsoft.com/en-us/agent-framework/user-guide/workflows/checkpoints?pivots=programming-language-python
- GitHub Actions: security hardening https://docs.github.com/en/actions/reference/security/secure-use
- GitHub Actions: manual `workflow_dispatch` https://docs.github.com/en/actions/how-tos/manage-workflow-runs/manually-run-a-workflow
- GitHub Actions: events triggered by the `GITHUB_TOKEN` https://docs.github.com/en/actions/how-tos/write-workflows/choose-when-workflows-run/trigger-a-workflow