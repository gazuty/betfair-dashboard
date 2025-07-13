function onOpen() {
  var ui = SpreadsheetApp.getUi();
  ui.createMenu('📊 Dashboard')
    .addItem('Refresh Charts', 'createDashboardCharts')
    .addToUi();
}

function createDashboardCharts() {
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var dash = ss.getSheetByName('Dashboard');

  // Remove all existing charts
  dash.getCharts().forEach(function(chart) {
    dash.removeChart(chart);
  });

  var chartConfigs = [
    { sheet: 'By Month',   cols: ['A', 'B'], title: 'Profit/Loss by Month', anchor: 2 },
    { sheet: 'By Day', cols: ['A', 'B'], title: 'Profit/Loss by Day', anchor: 20 },
    { sheet: 'By Day', cols: ['A', 'C'], title: 'Cumulative Profit/Loss', anchor: 38, type: Charts.ChartType.LINE },
    { sheet: 'By Week',    cols: ['A', 'B'], title: 'Profit/Loss by Week',  anchor: 56 },
    { sheet: 'By Sport',   cols: ['A', 'B'], title: 'Profit/Loss by Sport', anchor: 74 },
    { sheet: 'Top Horse Tracks', cols: ['B', 'C'], title: 'Top 15 Horse Tracks', anchor: 92 },
    { sheet: 'Bottom Horse Tracks', cols: ['B', 'C'], title: 'Bottom 15 Horse Tracks', anchor: 110 },
    { sheet: 'Top Strike Rates', cols: ['B', 'C'], title: 'Top 15 Strike Rates', anchor: 128 },
    { sheet: 'Bottom Strike Rates', cols: ['B', 'C'], title: 'Bottom 15 Strike Rates', anchor: 146 },
    { sheet: 'Horse Racing Daily', cols: ['A', 'B'], title: 'Horse Racing Daily P/L', anchor: 164 },
    { sheet: 'Horse Racing Daily', cols: ['A', 'C'], title: 'Horse Racing Cumulative', anchor: 182, type: Charts.ChartType.LINE },
    { sheet: 'Greyhound Racing Daily', cols: ['A', 'B'], title: 'Greyhound Racing Daily P/L', anchor: 200 },
    { sheet: 'Greyhound Racing Daily', cols: ['A', 'C'], title: 'Greyhound Cumulative', anchor: 218, type: Charts.ChartType.LINE }
  ];

  chartConfigs.forEach(function(cfg) {
    var sourceSheet = ss.getSheetByName(cfg.sheet);
    if (!sourceSheet) {
      Logger.log("❌ Sheet not found: " + cfg.sheet);
      return;
    }

    var lastRow = sourceSheet.getLastRow();
    if (lastRow < 2) {
      Logger.log("⚠️ No data in sheet: " + cfg.sheet);
      return;
    }

    // Log the exact range
    var rangesStr = cfg.cols.map(function(col) {
      return col + "2:" + col + lastRow;
    }).join(", ");
    Logger.log("📌 Building chart for " + cfg.title + " from ranges: " + rangesStr);

    // Build chart
    var chartBuilder = dash.newChart().setChartType(cfg.type || Charts.ChartType.COLUMN);

    cfg.cols.forEach(function(col) {
      chartBuilder.addRange(sourceSheet.getRange(col + "2:" + col + lastRow));
    });

    // Optional formatting for time-series charts
    if (cfg.type === Charts.ChartType.LINE && cfg.cols[0] === 'A') {
      chartBuilder.setOption('hAxis', { format: 'dd-MMM', title: 'Date' });
    }

    var chart = chartBuilder
      .setPosition(cfg.anchor, 4, 0, 0)
      .setOption('title', cfg.title)
      .build();

    dash.insertChart(chart);

    // Apply numeric formatting
    cfg.cols.forEach(function(col) {
      if (col !== 'A') {
        var rng = sourceSheet.getRange(col + "2:" + col + lastRow);
        rng.setNumberFormat("#,##0.00");
      }
    });

    Logger.log("✅ Chart added: " + cfg.title);
  });
}
