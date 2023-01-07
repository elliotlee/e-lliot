var multipleCardCarousel = document.querySelector(
  "#carouselExampleControls"
);
if (window.matchMedia("(min-width: 768px)").matches) {
  var carousel = new bootstrap.Carousel(multipleCardCarousel, {
    interval: false,
  });
  var carouselWidth = document.querySelector(".carousel-inner")[0].scrollWidth;
  var cardWidth = document.querySelector(".carousel-item").width();
  var scrollPosition = 0;
  document.querySelector("#carouselExampleControls .carousel-control-next").addEventListener("click", function () {
    if (scrollPosition < carouselWidth - cardWidth * 4) {
      scrollPosition += cardWidth;
      document.querySelector("#carouselExampleControls .carousel-inner").animate(
        { scrollLeft: scrollPosition },
        600
      );
    }
  });
  document.querySelector("#carouselExampleControls .carousel-control-prev").addEventListener("click", function () {
    if (scrollPosition > 0) {
      scrollPosition -= cardWidth;
      document.querySelector("#carouselExampleControls .carousel-inner").animate(
        { scrollLeft: scrollPosition },
        600
      );
    }
  });
} else {
  document.querySelector(multipleCardCarousel).classList.add("slide");
}





