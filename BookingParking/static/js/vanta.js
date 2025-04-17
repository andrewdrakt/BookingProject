document.addEventListener("DOMContentLoaded", function () {
  if (!document.body.classList.contains("with-vanta")) return;

  VANTA.RINGS({
    el: "#vanta-bg",
    mouseControls: true,
    touchControls: true,
    gyroControls: false,
    minHeight: 200.00,
    minWidth: 200.00,
    scale: 1.00,
    scaleMobile: 1.00,
    backgroundColor: 0x0a0a23,
    color: 0x2282a9
  });
});
