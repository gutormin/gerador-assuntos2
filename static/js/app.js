// Função de "copiar título" dos cards de assunto.
// Copia o texto para a área de transferência e registra o uso no servidor.
document.addEventListener("DOMContentLoaded", function () {
  document.querySelectorAll(".btn-copiar").forEach(function (btn) {
    btn.addEventListener("click", function () {
      const texto = btn.getAttribute("data-texto");
      const id = btn.getAttribute("data-id");

      // copia para a área de transferência
      navigator.clipboard.writeText(texto).then(function () {
        const original = btn.textContent;
        btn.textContent = "Copiado!";
        setTimeout(function () { btn.textContent = original; }, 1500);
      }).catch(function () {
        // fallback caso o navegador bloqueie a API de clipboard
        const tmp = document.createElement("textarea");
        tmp.value = texto;
        document.body.appendChild(tmp);
        tmp.select();
        document.execCommand("copy");
        document.body.removeChild(tmp);
        btn.textContent = "Copiado!";
      });

      // registra o uso no servidor (incrementa contador)
      fetch("/assunto/" + id + "/copiar", { method: "POST" });
    });
  });
});
