// Fonctions JS transverses (toasts, appels AJAX génériques).
const translations = {
  fr: {
    solution:"Solution",benefits:"Bénéfices",trust:"Confiance",dashboard:"Tableau de bord",login:"Connexion",subscribe:"Souscrire",news:"Actualités",schoolLevels:"Établissements",
    heroEyebrow:"L’école connectée, humaine et accessible",heroTitle:"Une seule plateforme pour rapprocher les familles, les écoles et les enseignants.",
    heroText:"Arthena simplifie les inscriptions, rend le suivi scolaire transparent et donne aux équipes éducatives les bons outils pour agir au bon moment.",
    startNow:"Commencer maintenant",discover:"Découvrir Arthena",privacyFirst:"Confidentialité, contrôle d’accès et traçabilité dès la conception.",
    onePortal:"1 portail",onePortalText:"pour toute la vie scolaire",fourRoles:"4 espaces",fourRolesText:"adaptés à chaque acteur",
    twoLanguages:"FR + EN",twoLanguagesText:"pour une adoption inclusive",mobileFirst:"Mobile first",mobileFirstText:"pensé pour le terrain",
    dailyNeeds:"Des besoins quotidiens, une réponse claire",solutionTitle:"Moins de démarches. Plus de visibilité. Davantage de temps pour apprendre.",
    families:"Pour les familles",familiesText:"Inscriptions centralisées, notes, absences, paiements et alertes importantes dans un espace sécurisé.",
    schools:"Pour les établissements",schoolsText:"Dossiers mieux organisés, validation rapide, pilotage des effectifs et communication structurée.",
    teachers:"Pour les enseignants",teachersText:"Appel, notes, remarques, planning et candidatures multi-écoles réunis dans une interface simple.",
    whySubscribe:"Pourquoi souscrire ?",benefitTitle:"Une relation école-famille plus fluide et plus responsable.",
    benefit1:"Réduire les déplacements et les dossiers éparpillés.",benefit2:"Détecter plus tôt absences, retards et difficultés.",
    benefit3:"Recevoir les informations importantes par email.",benefit4:"Retrouver des données cohérentes, accessibles selon votre rôle.",
    unescoPoint:"Le numérique éducatif doit rester centré sur l’apprenant, soutenir l’interaction humaine et être pertinent, équitable, fondé sur des preuves et durable.",
    expertView:"Ce que les références internationales nous enseignent",trustTitle:"La technologie est utile lorsqu’elle renforce la communauté éducative.",
    humanCentered:"Centrée sur l’humain",humanCenteredText:"Arthena accompagne les échanges entre personnes ; elle ne remplace ni l’enseignant ni le dialogue familial.",
    familyEngagement:"Familles engagées",familyEngagementText:"L’UNICEF souligne l’importance de la collaboration avec les parents et les communautés dans l’apprentissage numérique.",
    responsibleEvidence:"Choix responsables",responsibleEvidenceText:"Nous privilégions l’utilité, la sécurité et les résultats concrets plutôt que la technologie pour elle-même.",
    ready:"Prêt à simplifier la vie scolaire ?",ctaTitle:"Rejoignez une communauté qui place la réussite de chaque élève au centre.",
    createAccount:"Créer un compte",footerText:"Une plateforme scolaire plus proche, plus claire et plus sûre.",
    homeSchools:"Accueil & écoles",myStudents:"Mes élèves",newEnrollment:"Nouvelle inscription",ranking:"Classement",logout:"Déconnexion",
    builtForCameroon:"Pensée pour le Cameroun",fromPrimaryToHigh:"Du primaire au lycée",cameroonSchools:"Chaque établissement camerounais compte",schoolLevelsTitle:"Une continuité numérique du primaire au lycée.",schoolLevelsText:"Arthena respecte les réalités des écoles publiques et privées, francophones et anglophones, en ville comme dans les zones moins connectées.",
    primary:"Primaire",primaryText:"Créer tôt un lien de confiance : inscription, présence, progression et messages essentiels accessibles aux familles.",college:"Collège",collegeText:"Suivre les matières, anticiper le décrochage et aider chaque adolescent à construire son orientation.",highSchool:"Lycée",highSchoolText:"Préparer examens et avenir professionnel avec des données claires, une communication rapide et un meilleur accompagnement.",
    sharedProgress:"Une réussite partagée",stakeholderTitle:"Des bénéfices concrets pour ceux qui font vivre l’école.",teacherBenefits:"Ce que gagnent les enseignants",teacherGain1:"Moins de registres répétitifs et plus de temps pédagogique.",teacherGain2:"Une vue claire des absences, notes et besoins de chaque classe.",teacherGain3:"Des échanges traçables avec l’établissement et les familles.",teacherGain4:"Une meilleure visibilité des opportunités et candidatures auprès des écoles.",teacherGain5:"La valorisation du travail accompli et du suivi régulier.",
    schoolBenefits:"Ce que gagnent les établissements",schoolGain1:"Une administration structurée des inscriptions et des effectifs.",schoolGain2:"Des indicateurs fiables pour agir avant qu’un problème s’aggrave.",schoolGain3:"Une communication cohérente qui renforce la confiance des familles.",schoolGain4:"Une image moderne et transparente, favorable aux nouvelles inscriptions.",schoolGain5:"Des données centralisées avec des accès limités selon les responsabilités.",
    parentBenefits:"Ce que gagnent les parents",parentGain1:"Être informés rapidement des absences, notes et décisions importantes.",parentGain2:"Réduire les déplacements et conserver les démarches au même endroit.",parentGain3:"Mieux dialoguer avec les équipes éducatives sur des faits précis.",parentGain4:"Comparer les établissements avec des informations plus lisibles.",parentGain5:"Accompagner l’enfant aujourd’hui pour préparer son métier de demain.",
    futureStarts:"L’avenir commence dans nos écoles",futureTitle:"Chaque présence, chaque progrès et chaque encouragement construit le Cameroun de demain.",futureText:"Médecins, ingénieurs, enseignants, entrepreneurs, agriculteurs modernes, artistes ou chercheurs : mieux relier l’école et la famille aide chaque jeune à transformer son potentiel en projet.",
    stayInformed:"Comprendre pour mieux décider",landingNewsTitle:"L’actualité éducative du Cameroun, réunie au même endroit.",landingNewsText:"Décisions officielles, examens, établissements, enseignants et innovations : une veille intelligente actualisée quotidiennement, avec la source originale.",verifiedWatch:"Une veille utile, transparente et vérifiable",verifiedWatchText:"Le système collecte, déduplique et classe les sujets éducatifs. Il n’invente jamais d’information lorsque les sources sont indisponibles.",seeNews:"Voir les actualités",
    newsWatch:"Veille éducative camerounaise",newsTitle:"Actualités des écoles et décisions officielles",newsIntro:"Une sélection actualisée chaque jour, classée par pertinence et toujours reliée à sa source.",dailyUpdate:"Actualisation quotidienne",allNews:"Tout",decisions:"Décisions",institutions:"Établissements",exams:"Examens",innovation:"Innovation"
  },
  en: {
    solution:"Solution",benefits:"Benefits",trust:"Trust",dashboard:"Dashboard",login:"Sign in",subscribe:"Join now",news:"News",schoolLevels:"Schools",
    heroEyebrow:"Connected, human and accessible education",heroTitle:"One platform bringing families, schools and teachers closer together.",
    heroText:"Arthena simplifies enrolment, makes school progress transparent and gives education teams the right tools to act at the right time.",
    startNow:"Get started",discover:"Discover Arthena",privacyFirst:"Privacy, access control and accountability by design.",
    onePortal:"1 portal",onePortalText:"for the entire school journey",fourRoles:"4 spaces",fourRolesText:"tailored to every stakeholder",
    twoLanguages:"FR + EN",twoLanguagesText:"for inclusive adoption",mobileFirst:"Mobile first",mobileFirstText:"designed for real-world use",
    dailyNeeds:"Everyday needs, one clear answer",solutionTitle:"Less paperwork. More visibility. More time for learning.",
    families:"For families",familiesText:"Centralised enrolment, grades, attendance, payments and important alerts in a secure space.",
    schools:"For schools",schoolsText:"Better organised files, faster validation, enrolment insights and structured communication.",
    teachers:"For teachers",teachersText:"Attendance, grades, feedback, schedules and multi-school applications in one simple interface.",
    whySubscribe:"Why join?",benefitTitle:"A smoother, more accountable relationship between schools and families.",
    benefit1:"Reduce travel and scattered paperwork.",benefit2:"Identify absences, delays and learning difficulties earlier.",
    benefit3:"Receive important information by email.",benefit4:"Access consistent data according to your role.",
    unescoPoint:"Education technology should remain learner-centred, support human interaction and be appropriate, equitable, evidence-based and sustainable.",
    expertView:"What international evidence teaches us",trustTitle:"Technology matters when it strengthens the education community.",
    humanCentered:"Human-centred",humanCenteredText:"Arthena supports human relationships; it never replaces teachers or family dialogue.",
    familyEngagement:"Engaged families",familyEngagementText:"UNICEF highlights collaboration with parents and communities as a pillar of digital learning.",
    responsibleEvidence:"Responsible choices",responsibleEvidenceText:"We prioritise usefulness, safety and measurable outcomes over technology for its own sake.",
    ready:"Ready to simplify school life?",ctaTitle:"Join a community that puts every learner’s success first.",
    createAccount:"Create an account",footerText:"A closer, clearer and safer school platform.",
    homeSchools:"Home & schools",myStudents:"My students",newEnrollment:"New enrolment",ranking:"Ranking",logout:"Sign out",
    builtForCameroon:"Built for Cameroon",fromPrimaryToHigh:"From primary to high school",cameroonSchools:"Every Cameroonian school matters",schoolLevelsTitle:"One digital journey from primary to high school.",schoolLevelsText:"Arthena addresses the realities of public and private, French- and English-speaking schools, in cities and less connected areas.",
    primary:"Primary school",primaryText:"Build trust early through enrolment, attendance, progress and essential family messages.",college:"Middle school",collegeText:"Track subjects, anticipate dropout risks and help each teenager shape their pathway.",highSchool:"High school",highSchoolText:"Prepare for exams and careers with clear data, fast communication and better support.",
    sharedProgress:"Shared progress",stakeholderTitle:"Concrete benefits for everyone who brings education to life.",teacherBenefits:"Benefits for teachers",teacherGain1:"Less repetitive paperwork and more teaching time.",teacherGain2:"A clear view of attendance, grades and class needs.",teacherGain3:"Traceable communication with schools and families.",teacherGain4:"Better visibility of opportunities and school applications.",teacherGain5:"Recognition of consistent work and learner support.",
    schoolBenefits:"Benefits for schools",schoolGain1:"Structured enrolment and student administration.",schoolGain2:"Reliable indicators to act before problems escalate.",schoolGain3:"Consistent communication that strengthens family trust.",schoolGain4:"A modern, transparent image that supports enrolment.",schoolGain5:"Centralised data with role-based access.",
    parentBenefits:"Benefits for parents",parentGain1:"Quick information about absences, grades and key decisions.",parentGain2:"Less travel and every process in one place.",parentGain3:"Better dialogue with educators based on clear facts.",parentGain4:"Clearer information when comparing schools.",parentGain5:"Support children today as they prepare for tomorrow’s careers.",
    futureStarts:"The future starts in our schools",futureTitle:"Every attendance, achievement and encouragement builds tomorrow’s Cameroon.",futureText:"Doctors, engineers, teachers, entrepreneurs, modern farmers, artists or researchers: connecting school and family helps every learner turn potential into a plan.",
    stayInformed:"Understand more, decide better",landingNewsTitle:"Cameroon’s education news in one place.",landingNewsText:"Official decisions, exams, schools, teachers and innovation: an intelligent daily watch with every original source.",verifiedWatch:"Useful, transparent and verifiable monitoring",verifiedWatchText:"The system collects, deduplicates and ranks education topics. It never invents news when sources are unavailable.",seeNews:"View news",
    newsWatch:"Cameroon education watch",newsTitle:"School news and official decisions",newsIntro:"A daily selection ranked by relevance and always linked to its source.",dailyUpdate:"Updated daily",allNews:"All",decisions:"Decisions",institutions:"Schools",exams:"Exams",innovation:"Innovation"
  }
};

function applyLanguage(lang) {
  const selected = translations[lang] ? lang : "fr";
  document.documentElement.lang = selected;
  localStorage.setItem("arthena-language", selected);
  document.querySelectorAll("[data-i18n]").forEach((element) => {
    const translated = translations[selected][element.dataset.i18n];
    if (translated) element.textContent = translated;
  });
  document.querySelectorAll("[data-language-toggle]").forEach((button) => {
    button.textContent = selected === "fr" ? "EN" : "FR";
  });
}

function applyTheme(theme) {
  const selected = theme === "dark" ? "dark" : "light";
  document.documentElement.dataset.theme = selected;
  localStorage.setItem("arthena-theme", selected);
  document.querySelectorAll("[data-theme-toggle] i").forEach((icon) => {
    icon.className = selected === "dark" ? "fas fa-sun" : "fas fa-moon";
  });
}

applyTheme(localStorage.getItem("arthena-theme") || "light");

function toast(msg, type = "ok") {
  const el = document.createElement("div");
  el.className = `toast ${type}`;
  el.textContent = msg;
  const container = document.getElementById("toasts");
  if (!container) return;
  container.appendChild(el);
  setTimeout(() => el.remove(), 3500);
}

async function postJSON(url, data) {
  const res = await fetch(url, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "Accept": "application/json",
      "X-CSRFToken": document.querySelector('meta[name="csrf-token"]')?.content || "",
    },
    body: JSON.stringify(data),
  });
  const contentType = res.headers.get("content-type") || "";
  const payload = contentType.includes("application/json")
    ? await res.json()
    : { error: "Le serveur a renvoyé une réponse inattendue." };
  if (!res.ok) throw new Error(payload.error || `Erreur HTTP ${res.status}`);
  return payload;
}

document.addEventListener("submit", async (event) => {
  const form = event.target.closest("form[data-api-form]");
  if (!form) return;
  event.preventDefault();
  const submit = form.querySelector('[type="submit"]');
  if (submit) submit.disabled = true;
  try {
    if (form.enctype === "multipart/form-data") {
      const response = await fetch(form.action, {
        method: "POST",
        headers: {"X-CSRFToken": document.querySelector('meta[name="csrf-token"]')?.content || ""},
        body: new FormData(form),
      });
      const payload = await response.json();
      if (!response.ok) throw new Error(payload.error || `Erreur HTTP ${response.status}`);
    } else {
      const data = Object.fromEntries(new FormData(form).entries());
      await postJSON(form.action, data);
    }
    toast(form.dataset.success || "Opération effectuée.");
    if (form.dataset.reset === "true") form.reset();
    if (form.dataset.reload === "true") window.location.reload();
  } catch (error) {
    toast(error.message, "error");
  } finally {
    if (submit) submit.disabled = false;
  }
});

document.addEventListener("click", async (event) => {
  const button = event.target.closest("[data-api-action]");
  if (!button) return;
  event.preventDefault();
  button.disabled = true;
  try {
    await postJSON(button.dataset.apiAction, {});
    toast(button.dataset.success || "Opération effectuée.");
    button.closest("[data-removable]")?.remove();
  } catch (error) {
    toast(error.message, "error");
    button.disabled = false;
  }
});

document.querySelector("[data-sidebar-toggle]")?.addEventListener("click", (event) => {
  const open = document.body.classList.toggle("sidebar-open");
  event.currentTarget.setAttribute("aria-expanded", String(open));
});
document.querySelector("[data-sidebar-close]")?.addEventListener("click", () => {
  document.body.classList.remove("sidebar-open");
});

document.querySelectorAll("[data-language-toggle]").forEach((button) => {
  button.addEventListener("click", () => {
    applyLanguage(document.documentElement.lang === "fr" ? "en" : "fr");
  });
});
document.querySelectorAll("[data-theme-toggle]").forEach((button) => {
  button.addEventListener("click", () => {
    applyTheme(document.documentElement.dataset.theme === "dark" ? "light" : "dark");
  });
});
applyLanguage(localStorage.getItem("arthena-language") || "fr");

const returningStudent = document.querySelector('[data-form-toggle="returning-student"]');
const newSchoolReason = document.querySelector("[data-new-school-reason]");
function updateSchoolReason() {
  if (!returningStudent || !newSchoolReason) return;
  newSchoolReason.hidden = returningStudent.checked;
  const field = newSchoolReason.querySelector("textarea");
  if (field) field.required = !returningStudent.checked;
}
returningStudent?.addEventListener("change", updateSchoolReason);
updateSchoolReason();

document.addEventListener("click", (event) => {
  const tab = event.target.closest("[data-tab-target]");
  if (!tab) return;
  const group = tab.closest("[data-tabs]");
  group.querySelectorAll("[data-tab-target]").forEach((el) => el.classList.remove("active"));
  group.querySelectorAll("[data-tab-panel]").forEach((el) => el.hidden = true);
  tab.classList.add("active");
  group.querySelector(`[data-tab-panel="${tab.dataset.tabTarget}"]`).hidden = false;
});

document.querySelectorAll("[data-news-filter]").forEach((button) => {
  button.addEventListener("click", () => {
    const filter = button.dataset.newsFilter;
    document.querySelectorAll("[data-news-filter]").forEach((item) => item.classList.toggle("active", item === button));
    document.querySelectorAll("[data-news-category]").forEach((card) => {
      card.hidden = filter !== "all" && card.dataset.newsCategory !== filter;
    });
  });
});

document.querySelectorAll("[data-slideshow]").forEach((slideshow) => {
  const slides = [...slideshow.querySelectorAll(":scope > img")];
  const dots = slideshow.querySelector(".slide-dots");
  if (slides.length < 2 || !dots) return;
  let active = 0;
  let timer;
  const show = (index) => {
    active = (index + slides.length) % slides.length;
    slides.forEach((slide, position) => slide.classList.toggle("active", position === active));
    [...dots.children].forEach((dot, position) => dot.classList.toggle("active", position === active));
  };
  const restart = () => {
    clearInterval(timer);
    timer = setInterval(() => show(active + 1), Number(slideshow.dataset.interval) || 4500);
  };
  slides.forEach((_, index) => {
    const dot = document.createElement("button");
    dot.type = "button";
    dot.setAttribute("aria-label", `Image ${index + 1}`);
    dot.addEventListener("click", () => { show(index); restart(); });
    dots.appendChild(dot);
  });
  show(0);
  restart();
});

const schoolMapElement = document.querySelector("[data-school-map]");
if (schoolMapElement && window.L) {
  const map = L.map(schoolMapElement, {scrollWheelZoom: false}).setView([7.3697, 12.3547], 6);
  L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
    maxZoom: 19,
    attribution: "&copy; OpenStreetMap",
  }).addTo(map);
  const latitudeField = document.querySelector("[data-school-lat]");
  const longitudeField = document.querySelector("[data-school-lng]");
  const selectedLocation = document.querySelector("[data-selected-location]");
  const searchField = document.querySelector("[data-school-search]");
  const searchButton = document.querySelector("[data-school-search-button]");
  const resultBox = document.querySelector("[data-school-results]");
  const regionField = document.querySelector("[data-school-region]");
  const cityField = document.querySelector("[data-school-city]");
  let marker;

  const selectPosition = (lat, lng, label = "Position sélectionnée") => {
    if (!marker) {
      marker = L.marker([lat, lng], {draggable: true}).addTo(map);
      marker.on("dragend", () => {
        const position = marker.getLatLng();
        selectPosition(position.lat, position.lng, "Position ajustée manuellement");
      });
    } else {
      marker.setLatLng([lat, lng]);
    }
    latitudeField.value = Number(lat).toFixed(7);
    longitudeField.value = Number(lng).toFixed(7);
    selectedLocation.textContent = `${label} — ${Number(lat).toFixed(5)}, ${Number(lng).toFixed(5)}`;
    map.setView([lat, lng], 16);
  };

  const searchLocation = async (specificQuery, autoSelect = false) => {
    const context = [specificQuery, cityField.value, regionField.value].filter(Boolean).join(", ");
    if (context.length < 3) return;
    searchButton.disabled = true;
    resultBox.textContent = "Recherche en cours…";
    try {
      const response = await fetch(`/api/v1/geocode?q=${encodeURIComponent(context)}`, {headers: {"Accept": "application/json"}});
      const payload = await response.json();
      if (!response.ok) throw new Error(payload.error || "Recherche impossible.");
      resultBox.replaceChildren();
      payload.forEach((result, index) => {
        const button = document.createElement("button");
        button.type = "button";
        button.textContent = result.label;
        button.addEventListener("click", () => {
          selectPosition(result.lat, result.lng, result.label);
          resultBox.replaceChildren();
        });
        resultBox.appendChild(button);
        if (autoSelect && index === 0) {
          map.setView([result.lat, result.lng], 12);
        }
      });
      if (!payload.length) resultBox.textContent = "Aucun emplacement trouvé. Essayez le quartier ou une adresse proche.";
    } catch (error) {
      resultBox.textContent = error.message;
    } finally {
      searchButton.disabled = false;
    }
  };
  searchButton.addEventListener("click", () => searchLocation(searchField.value));
  searchField.addEventListener("keydown", (event) => {
    if (event.key === "Enter") {
      event.preventDefault();
      searchLocation(searchField.value);
    }
  });
  const recenter = () => searchLocation("", true);
  regionField.addEventListener("change", recenter);
  cityField.addEventListener("change", recenter);
  map.on("click", (event) => selectPosition(event.latlng.lat, event.latlng.lng, "Position choisie sur la carte"));
}
