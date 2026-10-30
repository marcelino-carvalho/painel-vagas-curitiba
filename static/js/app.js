/**
 * Controlador principal da Interface de Administração do Painel de Vagas
 * Agência do Trabalhador de Curitiba
 */

(function () {
  const titleInput = document.getElementById("panel-title-input");
  const vagasInput = document.getElementById("vagas-textarea");
  const countCompaniesEl = document.getElementById("count-companies");
  const countJobsEl = document.getElementById("count-jobs");

  const btnPublish = document.getElementById("btn-publish");
  const btnExportPdf = document.getElementById("btn-export-pdf");
  const btnZoom = document.getElementById("btn-zoom");
  const btnClear = document.getElementById("btn-clear");
  const btnLoadSample65 = document.getElementById("btn-load-sample-65");
  const btnNewPanel = document.getElementById("btn-new-panel");

  const logoFileInput = document.getElementById("logo-file-input");
  const btnUploadLogo = document.getElementById("btn-upload-logo");
  const btnResetLogo = document.getElementById("btn-reset-logo");
  const logoThumbImg = document.getElementById("logo-thumb-img");
  const headerStyleSelect = document.getElementById("header-style-select");

  const statusBadge = document.getElementById("publish-status-badge");
  const publicUrlInput = document.getElementById("public-url-input");
  const btnCopyUrl = document.getElementById("btn-copy-url");
  const btnOpenPublic = document.getElementById("btn-open-public");

  const previewBoard = document.getElementById("preview-board");
  const previewLogoImg = document.getElementById("preview-logo-img");
  const previewTitleEl = document.getElementById("preview-main-title");
  const previewGridEl = document.getElementById("preview-grid");
  const previewFooterContainer = document.getElementById("preview-footer-container");

  const confirmModal = document.getElementById("confirm-clear-modal");
  const btnConfirmClearYes = document.getElementById("btn-confirm-clear-yes");
  const btnConfirmClearNo = document.getElementById("btn-confirm-clear-no");

  const zoomModal = document.getElementById("zoom-modal");
  const zoomModalBody = document.getElementById("zoom-modal-body");
  const btnCloseZoom = document.getElementById("btn-close-zoom");

  const toastEl = document.getElementById("toast-notification");

  const initialDataEl = document.getElementById("initial-boot-data");
  const bootData = initialDataEl ? JSON.parse(initialDataEl.textContent) : {};

  let currentSlug = bootData.initial_slug || null;
  let currentPublicUrl = bootData.initial_public_url || "";
  let currentQrDataUrl = bootData.initial_qr_data_url || "";
  let currentLogoDataUrl = null; // null = usar default_logo
  const defaultLogoDataUrl = bootData.default_logo_data_url || "";
  const sample65Text = bootData.sample_65_text || "";

  function showToast(message, type) {
    if (!toastEl) return;
    toastEl.textContent = message;
    toastEl.className = "toast-notification show " + (type || "success");
    clearTimeout(toastEl._timer);
    toastEl._timer = setTimeout(function () {
      toastEl.className = "toast-notification";
    }, 4000);
  }

  function shouldUseTwoCols(jobs) {
    if (!jobs || jobs.length < 5) return false;
    let maxLen = 0;
    for (let i = 0; i < jobs.length; i++) {
      if (jobs[i].length > maxLen) maxLen = jobs[i].length;
    }
    return maxLen <= 28;
  }

  function computePreviewScale(totalCompanies) {
    if (totalCompanies <= 14) return 1.1;
    if (totalCompanies <= 28) return 1.0;
    if (totalCompanies <= 42) return 0.92;
    if (totalCompanies <= 56) return 0.85;
    return 0.78;
  }

  function buildQrBoxElement() {
    const box = document.createElement("div");
    box.className = "panel-qr-box";

    const textDiv = document.createElement("div");
    textDiv.className = "panel-qr-text";
    textDiv.textContent = "ESCANEIE O QR CODE E ACESSE O PAINEL DE VAGAS PELO CELULAR!";

    if (currentPublicUrl) {
      const sub = document.createElement("span");
      sub.className = "panel-qr-sub";
      sub.textContent = currentPublicUrl;
      textDiv.appendChild(sub);
    }

    const arrow = document.createElement("div");
    arrow.className = "panel-qr-arrow";
    arrow.textContent = "➔";

    const qrImg = document.createElement("img");
    qrImg.className = "panel-qr-img";
    qrImg.src = currentQrDataUrl;
    qrImg.alt = "QR Code Público do Painel";

    box.appendChild(textDiv);
    box.appendChild(arrow);
    box.appendChild(qrImg);
    return box;
  }

  function renderPreview() {
    const titleVal = (titleInput.value || "").trim() || "MUTIRÃO EMPREGA + [NOME DO EVENTO] | CASA DO TRABALHADOR";
    const rawText = vagasInput.value || "";
    const parsed = window.VagasParser.parseVagasText(rawText);

    // Atualiza contadores
    countCompaniesEl.textContent = String(parsed.totalCompanies);
    countJobsEl.textContent = String(parsed.totalJobs);

    // Atualiza título e logotipo
    previewTitleEl.textContent = titleVal;
    const activeLogo = currentLogoDataUrl || defaultLogoDataUrl;
    previewLogoImg.src = activeLogo;
    logoThumbImg.src = activeLogo;

    // Atualiza estilo do cabeçalho das células
    const styleMode = headerStyleSelect ? headerStyleSelect.value : "dark";
    previewBoard.className = "panel-board style-" + styleMode;

    // Escala dinâmica de tipografia
    const scale = computePreviewScale(parsed.totalCompanies);
    previewBoard.style.setProperty("--preview-scale", String(scale));

    // Constrói células de empresas na grade de 7 colunas
    previewGridEl.innerHTML = "";
    previewFooterContainer.innerHTML = "";

    if (parsed.companies.length === 0) {
      const emptyDiv = document.createElement("div");
      emptyDiv.className = "panel-empty-state";
      emptyDiv.textContent = "Nenhuma empresa inserida. Digite ou cole a lista de empresas e vagas no campo acima para gerar o painel automaticamente.";
      previewGridEl.appendChild(emptyDiv);

      const footerBar = document.createElement("div");
      footerBar.className = "panel-footer-bar";
      footerBar.appendChild(buildQrBoxElement());
      previewFooterContainer.appendChild(footerBar);
      return;
    }

    parsed.companies.forEach(function (comp) {
      const cell = document.createElement("div");
      cell.className = "panel-cell";

      const header = document.createElement("div");
      header.className = "panel-cell-header";

      const numSpan = document.createElement("span");
      numSpan.className = "panel-cell-num";
      numSpan.textContent = String(comp.number);

      const nameSpan = document.createElement("span");
      nameSpan.className = "panel-cell-name";
      nameSpan.textContent = comp.name;

      header.appendChild(numSpan);
      header.appendChild(nameSpan);
      cell.appendChild(header);

      const ul = document.createElement("ul");
      ul.className = "panel-jobs-list" + (shouldUseTwoCols(comp.jobs) ? " two-cols" : "");

      comp.jobs.forEach(function (job) {
        const li = document.createElement("li");
        li.className = "panel-job-item";
        li.textContent = job;
        ul.appendChild(li);
      });

      cell.appendChild(ul);
      previewGridEl.appendChild(cell);
    });

    // Posiciona o QR Code no canto inferior direito (na última linha se sobrarem >= 2 colunas, ou em barra inferior)
    const remainder = parsed.companies.length % 7;
    const freeCols = remainder === 0 ? 0 : 7 - remainder;

    if (freeCols >= 2) {
      const qrInline = document.createElement("div");
      qrInline.className = "panel-qr-inline-cell";
      qrInline.style.gridColumn = "span " + freeCols;
      qrInline.appendChild(buildQrBoxElement());
      previewGridEl.appendChild(qrInline);
    } else {
      const footerBar = document.createElement("div");
      footerBar.className = "panel-footer-bar";
      footerBar.appendChild(buildQrBoxElement());
      previewFooterContainer.appendChild(footerBar);
    }
  }

  function updatePublishUI(isPublished) {
    if (isPublished && currentSlug && currentPublicUrl) {
      statusBadge.textContent = "Painel Publicado (Online)";
      statusBadge.className = "status-badge";
      publicUrlInput.value = currentPublicUrl;
      if (btnOpenPublic) {
        btnOpenPublic.href = currentPublicUrl;
        btnOpenPublic.style.pointerEvents = "auto";
        btnOpenPublic.style.opacity = "1";
      }
    } else {
      statusBadge.textContent = currentSlug ? "Alterações não publicadas" : "Aguardando Publicação";
      statusBadge.className = "status-badge draft";
    }
  }

  async function publishPanel(silent) {
    const titleVal = (titleInput.value || "").trim() || "MUTIRÃO EMPREGA + [NOME DO EVENTO] | CASA DO TRABALHADOR";
    const rawText = vagasInput.value || "";
    const parsed = window.VagasParser.parseVagasText(rawText);

    if (parsed.totalCompanies === 0) {
      showToast("Insira pelo menos uma empresa e vaga antes de publicar o painel.", "error");
      return null;
    }

    const originalText = btnPublish.textContent;
    btnPublish.disabled = true;
    btnPublish.textContent = "Publicando...";

    try {
      const response = await fetch("/api/panels", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          title: titleVal,
          raw_text: rawText,
          slug: currentSlug,
          logo_data_url: currentLogoDataUrl,
          header_style: headerStyleSelect ? headerStyleSelect.value : "dark",
        }),
      });

      if (!response.ok) {
        const errData = await response.json().catch(function () { return {}; });
        throw new Error(errData.detail || "Erro ao publicar o painel.");
      }

      const data = await response.json();
      currentSlug = data.slug;
      currentPublicUrl = data.public_url;
      currentQrDataUrl = data.qr_data_url;

      updatePublishUI(true);
      renderPreview();

      if (!silent) {
        showToast("Painel publicado com sucesso! O QR Code e o link público estão ativos.", "success");
      }
      return data;
    } catch (err) {
      showToast(err.message || "Falha ao publicar painel.", "error");
      return null;
    } finally {
      btnPublish.disabled = false;
      btnPublish.textContent = originalText;
    }
  }

  async function exportPdf() {
    const parsed = window.VagasParser.parseVagasText(vagasInput.value || "");
    if (parsed.totalCompanies === 0) {
      showToast("Insira pelo menos uma empresa antes de exportar o PDF.", "error");
      return;
    }

    const originalText = btnExportPdf.textContent;
    btnExportPdf.disabled = true;
    btnExportPdf.textContent = "Gerando PDF A4...";

    try {
      // Garante que o painel esteja publicado e atualizado no link público do QR Code
      const pubData = await publishPanel(true);
      if (!pubData || !pubData.slug) {
        return;
      }

      const pdfResponse = await fetch("/api/panels/" + encodeURIComponent(pubData.slug) + "/pdf");
      if (!pdfResponse.ok) {
        const errData = await pdfResponse.json().catch(function () { return {}; });
        throw new Error(errData.detail || "Erro ao gerar o PDF.");
      }

      const blob = await pdfResponse.blob();
      const downloadUrl = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = downloadUrl;
      a.download = "painel-vagas-" + pubData.slug + ".pdf";
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(downloadUrl);

      showToast("PDF A4 Paisagem exportado com sucesso com QR Code público!", "success");
    } catch (err) {
      showToast(err.message || "Erro na exportação do PDF.", "error");
    } finally {
      btnExportPdf.disabled = false;
      btnExportPdf.textContent = originalText;
    }
  }

  // Eventos de atualização em tempo real
  titleInput.addEventListener("input", function () {
    updatePublishUI(false);
    renderPreview();
  });

  vagasInput.addEventListener("input", function () {
    updatePublishUI(false);
    renderPreview();
  });

  if (headerStyleSelect) {
    headerStyleSelect.addEventListener("change", function () {
      updatePublishUI(false);
      renderPreview();
    });
  }

  // Upload e substituição do logotipo institucional
  btnUploadLogo.addEventListener("click", function () {
    logoFileInput.click();
  });

  logoFileInput.addEventListener("change", function (e) {
    const file = e.target.files && e.target.files[0];
    if (!file) return;
    if (!file.type.startsWith("image/")) {
      showToast("Selecione um arquivo de imagem válido (PNG, JPG, SVG ou WebP).", "error");
      return;
    }
    const reader = new FileReader();
    reader.onload = function (ev) {
      currentLogoDataUrl = ev.target.result;
      btnResetLogo.style.display = "inline-flex";
      updatePublishUI(false);
      renderPreview();
      showToast("Logotipo institucional atualizado na pré-visualização.", "success");
    };
    reader.readAsDataURL(file);
  });

  btnResetLogo.addEventListener("click", function () {
    currentLogoDataUrl = null;
    logoFileInput.value = "";
    btnResetLogo.style.display = "none";
    updatePublishUI(false);
    renderPreview();
    showToast("Logotipo institucional padrão restaurado.", "success");
  });

  // Limpar campo com confirmação obrigatória
  btnClear.addEventListener("click", function () {
    confirmModal.classList.add("open");
  });

  btnConfirmClearNo.addEventListener("click", function () {
    confirmModal.classList.remove("open");
  });

  btnConfirmClearYes.addEventListener("click", function () {
    vagasInput.value = "";
    confirmModal.classList.remove("open");
    updatePublishUI(false);
    renderPreview();
    vagasInput.focus();
    showToast("Campo de empresas e vagas limpo.", "success");
  });

  // Carregar exemplo completo de 65 empresas (Mutirão Pinheirinho)
  if (btnLoadSample65) {
    btnLoadSample65.addEventListener("click", function () {
      titleInput.value = "MUTIRÃO EMPREGA + PINHEIRINHO | CASA DO TRABALHADOR";
      vagasInput.value = sample65Text;
      updatePublishUI(false);
      renderPreview();
      showToast("Exemplo completo com 65 empresas carregado!", "success");
    });
  }

  // Criar novo painel (novo endereço exclusivo)
  if (btnNewPanel) {
    btnNewPanel.addEventListener("click", function () {
      currentSlug = null;
      publicUrlInput.value = "Será gerado ao clicar em PUBLICAR PAINEL";
      updatePublishUI(false);
      showToast("Modo Novo Painel ativado. A próxima publicação gerará um novo link exclusivo.", "success");
    });
  }

  // Copiar endereço público
  if (btnCopyUrl) {
    btnCopyUrl.addEventListener("click", function () {
      if (!currentPublicUrl) return;
      navigator.clipboard.writeText(currentPublicUrl).then(function () {
        showToast("Endereço público copiado para a área de transferência!", "success");
      });
    });
  }

  // Visualizar painel em tamanho ampliado (Modal Zoom)
  btnZoom.addEventListener("click", function () {
    zoomModalBody.innerHTML = "";
    const clone = previewBoard.cloneNode(true);
    clone.id = "preview-board-zoomed";
    clone.style.setProperty("--preview-scale", "1.05");
    zoomModalBody.appendChild(clone);
    zoomModal.classList.add("open");
  });

  btnCloseZoom.addEventListener("click", function () {
    zoomModal.classList.remove("open");
  });

  zoomModal.addEventListener("click", function (e) {
    if (e.target === zoomModal) {
      zoomModal.classList.remove("open");
    }
  });

  // Botões principais de Publicação e Exportação PDF
  btnPublish.addEventListener("click", function () {
    publishPanel(false);
  });

  btnExportPdf.addEventListener("click", function () {
    exportPdf();
  });

  // Inicialização
  updatePublishUI(Boolean(currentSlug));
  renderPreview();
})();
