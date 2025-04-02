// When the DOM content is loaded, start the progress bar and hide the loading popup
document.addEventListener("DOMContentLoaded", function () {
  let progressBar = document.getElementById("progress-bar");
  let loadingPopup = document.getElementById("web-loading");

  // Faster progress bar (loads in 15 seconds max)
  let progress = 0;
  let loadingInterval = setInterval(() => {
      if (progress < 100) {
          progress += 10;
          progressBar.style.width = progress + "%";
          progressBar.innerText = progress + "%";
      } else {
          clearInterval(loadingInterval);
          loadingPopup.style.display = "none"; // Hide loading screen
      }
  }, 500);

  // Force remove loading popup after 15s if still present
  setTimeout(() => {
      if (loadingPopup) loadingPopup.style.display = "none";
  }, 15000);
});

// Function to fetch stocks for a given category based on user input month
function fetchStocks(category) {
  let loadingText = document.getElementById("loading");
  let searchButton = document.getElementById("searchButton");
  let userMonth = document.getElementById("monthInput").value; // in YYYY-MM format

  // Show loading indicator and disable the button
  loadingText.style.display = "block";
  searchButton.disabled = true;

  fetch(`/stocks?category=${category}&date=${userMonth}`)
    .then(response => response.json())
    .then(data => {
      loadingText.style.display = "none";
      searchButton.disabled = false;

      let table = document.getElementById("stocksTable");
      table.innerHTML = "<tr><th>Symbol</th><th>LTP</th><th>All Time High</th><th>All Time Low</th><th>ATH Date</th></tr>";

      if (data.length === 0) {
        table.innerHTML += "<tr><td colspan='5' class='no-stocks'>No stocks found</td></tr>";
      } else {
        data.forEach(stock => {
          table.innerHTML += `<tr onclick="gotoStockDetails('${stock.symbol}')">
            <td>${stock.symbol}</td>
            <td>${stock.ltp}</td>
            <td>${stock.all_time_high}</td>
            <td>${stock.all_time_low}</td>
            <td>${stock.high_date}</td>
          </tr>`;
        });
      }
    })
    .catch(error => {
      loadingText.style.display = "none";
      searchButton.disabled = false;
      console.error("Error fetching data:", error);
    });
}

// Redirect to the stock details page
function gotoStockDetails(symbol) {
  window.location.href = `/stock-details/${symbol}`;
}

// Load ATH Stocks (from all categories)
function loadATHStocks() {
  fetch("/stocks?category=all")
    .then(response => response.json())
    .then(data => {
      let athContainer = document.getElementById("ath-stocks");
      let stocksHTML = data.map(stock =>
          `<span class="ath-stock">🚀 ${stock.symbol}: ₹${stock.ltp} (${stock.change}%)</span>`
      ).join(" ");
      athContainer.innerHTML = stocksHTML;
    })
    .catch(error => console.error("Error fetching ATH stocks:", error));
}

// Load Top Gainers & Losers stocks
function loadTopStocks() {
  fetch("/top-stocks")
    .then(response => response.json())
    .then(data => {
      document.getElementById("top-gainers").innerHTML = data.gainers.map(stock =>
          `<div class="stock-up">📈 ${stock.symbol}: ₹${stock.ltp} (${stock.change}%)</div>`
      ).join("");

      document.getElementById("top-losers").innerHTML = data.losers.map(stock =>
          `<div class="stock-down">📉 ${stock.symbol}: ₹${stock.ltp} (${stock.change}%)</div>`
      ).join("");
    })
    .catch(error => console.error("Error fetching top stocks:", error));
}

// Render the Sector Chart using Plotly
function renderSectorChart() {
  fetch("/sector-data")
    .then(response => response.json())
    .then(data => {
      Plotly.newPlot("sector-chart", [{
          labels: Object.keys(data),
          values: Object.values(data),
          type: "pie"
      }], { title: "📊 Sector-wise Stock Distribution" });
    })
    .catch(error => console.error("Error fetching sector data:", error));
}

// Initialize functions when the window loads
window.onload = function () {
  loadATHStocks();
  loadTopStocks();
  renderSectorChart();
};
function showLoading() {
  document.getElementById("loading").style.display = "block";
}

function hideLoading() {
  document.getElementById("loading").style.display = "none";
}
