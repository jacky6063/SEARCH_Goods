export function applyPromoLine(rootSelector = ".goods-list") {
  const root = document.querySelector(rootSelector) || document;
  const cards = root.querySelectorAll("[data-good-id], .product-card");
  cards.forEach(card => {
    if (card.querySelector(".promo-40")) return;
    const promo =
      card.dataset.promo ||
      card.getAttribute("data-promo") ||
      (card.querySelector("[data-promo]")?.getAttribute("data-promo") || "");
    if (!promo) return;
    const titleEl = card.querySelector(".title, .goods-title, h3, .name");
    const insertAt = titleEl ? titleEl.parentElement : card;
    const p = document.createElement("div");
    p.className = "promo-40";
    p.style.fontSize = "0.9rem";
    p.style.color = "#6B7280";
    p.style.lineHeight = "1.4";
    p.style.marginTop = "4px";
    p.textContent = promo;
    if (titleEl && titleEl.nextSibling) {
      insertAt.insertBefore(p, titleEl.nextSibling);
    } else {
      insertAt.prepend(p);
    }
  });
}
