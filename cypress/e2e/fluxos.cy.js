/// <reference types="cypress" />

// Testes E2E do dashboard Client Desk contra o backend FastAPI rodando em
// http://127.0.0.1:8000. Exercitam os dois fluxos pela própria UI, validando
// também a autenticação (login JWT) e que o painel "Live Wire" exibe as
// mutations GraphQL reais do Pipefy.

const ADMIN = { email: "admin@mundoinvest.com", password: "admin123" };

describe("Client Desk · fluxos Pipefy (E2E)", () => {
  // E-mail único por execução: o SQLite local persiste entre rodadas.
  const email = `e2e_${Date.now()}@example.com`;
  const eventId = `evt_e2e_${Date.now()}`;

  // Desativa animações de entrada/flash para screenshots estáveis e limpos.
  const stabilize = () =>
    cy.document().then((doc) => {
      const s = doc.createElement("style");
      s.innerHTML =
        "*{animation-duration:0s!important;animation-delay:0s!important;transition:none!important}" +
        ".reveal{opacity:1!important;transform:none!important}";
      doc.head.appendChild(s);
    });

  // Visita já autenticado (login programático) — rápido e isolado por teste.
  const visitAuthed = () => {
    cy.request("POST", "/login", ADMIN).then((resp) => {
      const token = resp.body.access_token;
      cy.visit("/", {
        onBeforeLoad(win) {
          win.localStorage.setItem("cd_token", token);
          win.localStorage.setItem("cd_email", ADMIN.email);
        },
      });
    });
    stabilize();
  };

  it("Auth · exige login e autentica via UI", () => {
    cy.visit("/");
    stabilize();
    // Sem token, o overlay de login aparece e o app fica protegido.
    cy.get("#login").should("be.visible");

    cy.get('#formLogin input[name="email"]').type(ADMIN.email);
    cy.get('#formLogin input[name="password"]').type(ADMIN.password);
    cy.get('#formLogin button[type="submit"]').click();

    // Autenticado: overlay some e o chip do usuário aparece.
    cy.get("#login").should("not.be.visible");
    cy.get("#userChip").should("be.visible");
    cy.get("#userEmail").should("have.text", ADMIN.email);
    cy.contains("h1", "Patrimônio sob controle");
    cy.screenshot("00-login");
  });

  it("Auth · credenciais inválidas mostram erro", () => {
    cy.visit("/");
    stabilize();
    cy.get('#formLogin input[name="email"]').type(ADMIN.email);
    cy.get('#formLogin input[name="password"]').type("senha-errada");
    cy.get('#formLogin button[type="submit"]').click();
    cy.get("#loginErr").should("contain", "Email ou Senha incorretos.");
    cy.get("#login").should("be.visible");
  });

  it("Fluxo 1 · cria cliente e exibe a mutation createCard no Live Wire", () => {
    visitAuthed();

    cy.get('input[name="cliente_nome"]').type("Cliente E2E");
    cy.get('input[name="cliente_email"]').type(email);
    cy.get('select[name="tipo_solicitacao"]').select("Aporte");
    cy.get('input[name="valor_patrimonio"]').type("250000");
    cy.get('#formCliente button[type="submit"]').click();

    // Feedback + persistência na tabela.
    cy.get("#toasts").contains("Cliente criado");
    cy.get("#tbody").contains(email);
    cy.get("#tbody").contains("Aguardando Análise");
    cy.get("#tbody").contains("R$ 250.000");

    // Live Wire: GraphQL real transmitido.
    cy.get("#wire").contains(".mut-name", "createCard");
    cy.get("#wire").contains("createCard(input: $input)");
    cy.get("#wire").contains('"pipe_id"');

    cy.screenshot("01-fluxo1-cliente-criado");
  });

  it("Fluxo 2 · webhook aplica prioridade alta e exibe updateCardField", () => {
    visitAuthed();

    cy.get("#whEmail").select(email);
    cy.get("#whEvent").clear().type(eventId);
    cy.get('#formWebhook button[type="submit"]').click();

    cy.get("#toasts").contains("Webhook processado");
    // 250.000 >= 200.000 -> prioridade alta + status processado na tabela.
    cy.get("#tbody")
      .contains("td", email)
      .parents("tr")
      .within(() => {
        cy.contains(".badge", "Processado");
        cy.contains(".badge", "Alta");
      });

    // Live Wire: duas mutations updateCardField (status + prioridade).
    cy.get("#wire").find(".mut").should("have.length", 2);
    cy.get("#wire").contains('"new_value": "Processado"');
    cy.get("#wire").contains('"new_value": "prioridade_alta"');

    cy.screenshot("02-fluxo2-webhook-processado");
  });

  it("Idempotência · reenviar o mesmo event_id é ignorado", () => {
    visitAuthed();

    // Reenvia exatamente o mesmo evento do teste anterior.
    cy.get("#whEmail").select(email);
    cy.get("#whEvent").clear().type(eventId);
    cy.get('#formWebhook button[type="submit"]').click();

    cy.get("#toasts").contains("Evento ignorado (idempotência)");
    cy.get("#toasts").contains("já processado");

    cy.screenshot("03-idempotencia-bloqueada");
  });
});
