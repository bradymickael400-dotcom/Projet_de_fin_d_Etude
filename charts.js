
// ══════════════════════════════════════════════════════
//  CHARTS
// ══════════════════════════════════════════════════════
function initCharts(page){
  Chart.defaults.color       = '#8fa3bc';
  Chart.defaults.borderColor = 'rgba(30,45,66,.6)';

  function mkChart(id, type, labels, datasets, opts={}){
    const el = document.getElementById(id);
    if(!el) return;
    if(charts[id]) charts[id].destroy();
    charts[id] = new Chart(el, {
      type, data:{labels, datasets},
      options:{
        responsive:true, maintainAspectRatio:false,
        plugins:{legend:{display:datasets.length>1,labels:{color:'#8fa3bc',boxWidth:12,font:{size:11}}},...(opts.plugins||{})},
        scales:(type==='doughnut'||type==='pie')?{}:{
          x:{grid:{color:'rgba(30,45,66,.5)'},ticks:{font:{size:10},maxTicksLimit:8}},
          y:{grid:{color:'rgba(30,45,66,.5)'},ticks:{font:{size:10}},...(opts.y||{})}
        },
        animation:{duration:600}, ...opts
      }
    });
    return charts[id];
  }

  mkChart('chart-temp',  'line', [], [{label:'Température (°C)', data:[], borderColor:'#00d4ff', backgroundColor:'rgba(0,212,255,.08)', borderWidth:2, fill:true, tension:.4, pointRadius:2}]);
  mkChart('chart-hum',   'line', [], [{label:'Humidité (%)',      data:[], borderColor:'#2979ff', backgroundColor:'rgba(41,121,255,.08)',borderWidth:2, fill:true, tension:.4, pointRadius:2}]);
  mkChart('chart-shock', 'bar',  [], [{label:'Chocs (G)',         data:[], backgroundColor:'#ffab00', borderRadius:4}]);
  mkChart('chart-press', 'line', [], [{label:'Pression (hPa)',    data:[], borderColor:'#b44dff', backgroundColor:'rgba(180,77,255,.08)', borderWidth:2, fill:true, tension:.4, pointRadius:2}]);
  mkChart('chart-speed', 'line', [], [{label:'Vitesse (km/h)',    data:[], borderColor:'#00e676', borderWidth:2, fill:false, tension:.4, pointRadius:2}]);
// Graphique de l'évolution du total des entreprises ARGOS
  mkChart('chart-revenue', 'line', [],
    [{
      label: 'Total entreprises enregistrées', 
      data: [],
      backgroundColor: 'rgba(0, 212, 255, 0.1)', // Fond bleuté transparent
      borderColor: 'var(--cyan)', 
      borderWidth: 2, 
      fill: true,        // Remplissage sous la courbe
      tension: 0.3,      // Courbe légèrement lissée
      pointBackgroundColor: '#fff',
      pointRadius: 3
    }]
  );
  mkChart('chart-subs', 'doughnut', ['Choc','Temp.','Humidité','Vitesse','Pression'],
    [{data:[], backgroundColor:['#ff4444','#ffab00','#2979ff','#00e676','#b44dff'], borderWidth:0, hoverOffset:6}]);
}