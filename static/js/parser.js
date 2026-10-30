/**
 * Módulo de interpretação em tempo real do texto de empresas e vagas (Client-Side).
 * Implementa rigorosamente as regras da Agência do Trabalhador de Curitiba:
 * - Primeira linha de cada bloco = Nome da empresa
 * - Linhas seguintes = Vagas oferecidas pela empresa
 * - Uma ou mais linhas em branco consecutivas = separador de nova empresa
 * - Ignora espaços extras no início/fim das linhas e linhas em branco no início/fim do texto
 * - Preserva acentos e caracteres especiais
 */

(function (global) {
  function parseVagasText(rawText) {
    if (!rawText || !rawText.trim()) {
      return {
        companies: [],
        totalCompanies: 0,
        totalJobs: 0,
      };
    }

    const normalized = rawText.replace(/\r\n/g, "\n").replace(/\r/g, "\n");
    const lines = normalized.split("\n");

    const blocks = [];
    let currentBlock = [];

    for (let i = 0; i < lines.length; i++) {
      const cleaned = lines[i].trim().replace(/[ \t]+/g, " ");
      if (cleaned === "") {
        if (currentBlock.length > 0) {
          blocks.push(currentBlock);
          currentBlock = [];
        }
      } else {
        currentBlock.push(cleaned);
      }
    }

    if (currentBlock.length > 0) {
      blocks.push(currentBlock);
    }

    const companies = [];
    let totalJobs = 0;

    for (let idx = 0; idx < blocks.length; idx++) {
      const block = blocks[idx];
      const companyName = block[0];
      const jobs = block.length > 1 ? block.slice(1) : [];
      totalJobs += jobs.length;

      companies.push({
        number: idx + 1,
        name: companyName,
        jobs: jobs,
        job_count: jobs.length,
      });
    }

    return {
      companies: companies,
      totalCompanies: companies.length,
      totalJobs: totalJobs,
    };
  }

  global.VagasParser = {
    parseVagasText: parseVagasText,
  };
})(window);
