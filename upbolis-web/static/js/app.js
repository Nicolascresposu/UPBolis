// Pequeños efectos pro: tilt de la tarjeta, focus en campos y ripple en el botón

document.addEventListener("DOMContentLoaded", () => {
  const tiltContainer = document.querySelector("[data-tilt-container]");
  const fields = document.querySelectorAll("[data-field] input");
  const submitBtn = document.querySelector("[data-ripple]");

  // Tilt 3D suave en el contenedor principal
  if (tiltContainer) {
    const strength = 8; // grados máximos

    tiltContainer.addEventListener("mousemove", (e) => {
      const rect = tiltContainer.getBoundingClientRect();
      const x = e.clientX - rect.left;
      const y = e.clientY - rect.top;
      const centerX = rect.width / 2;
      const centerY = rect.height / 2;

      const rotateX = ((y - centerY) / centerY) * -strength;
      const rotateY = ((x - centerX) / centerX) * strength;

      tiltContainer.style.transform =
        `perspective(1100px) rotateX(${rotateX}deg) rotateY(${rotateY}deg)`;
    });

    tiltContainer.addEventListener("mouseleave", () => {
      tiltContainer.style.transform = "perspective(1100px) rotateX(0deg) rotateY(0deg)";
    });
  }

  // Resaltar campo al focus
  fields.forEach((input) => {
    const field = input.closest("[data-field]");
    if (!field) return;

    input.addEventListener("focus", () => {
      field.classList.add("field--focused");
    });

    input.addEventListener("blur", () => {
      if (!input.value) {
        field.classList.remove("field--focused");
      }
    });
  });

  // Ripple en botón de login
  if (submitBtn) {
    submitBtn.addEventListener("click", (e) => {
      const rect = submitBtn.getBoundingClientRect();
      const ripple = document.createElement("span");
      ripple.classList.add("ripple");

      const x = e.clientX - rect.left;
      const y = e.clientY - rect.top;

      ripple.style.left = `${x}px`;
      ripple.style.top = `${y}px`;

      // eliminar ripple anterior si existe
      const previous = submitBtn.querySelector(".ripple");
      if (previous) previous.remove();

      submitBtn.appendChild(ripple);

      setTimeout(() => ripple.remove(), 500);
    });
  }
});
