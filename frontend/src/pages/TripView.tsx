import { useEffect, useState, useRef } from "react";

import BudgetAlerts from "../components/BudgetAlerts";
import AddExpenseModal from "../components/AddExpenseModal";
import BudgetBreakdown from "../components/BudgetBreakdown";
import BudgetCard from "../components/BudgetCard";
import BudgetPieChart from "../components/BudgetPieChart";
import BudgetStatus from "../components/BudgetStatus";
import Dashboard from "../components/Dashboard";
import DayCard from "../components/DayCard";
import ExpenseCard from "../components/ExpenseCard";
import ExpenseTable from "../components/ExpenseTable";
import MapView from "../components/MapView";
import SettlementCard from "../components/SettlementCard";
import WeatherCard from "../components/WeatherCard";
import TravelerConflicts from "../components/TravelerConflicts";
import TripInsightsCard from "../components/TripInsightsCard";

import { useNavigate } from "react-router-dom";

import {
  addExpense,
  getExpenses,
} from "../services/expense";

import PlaceDetailModal from "../components/PlaceDetailModal";
import TripShareModal from "../components/TripShareModal";
import CurrencySelector from "../components/CurrencySelector";
import WeatherAlertsBanner from "../components/WeatherAlertsBanner";
import { getTripWeatherAlerts } from "../services/weather";
import type { TripWeatherAlertsResponse } from "../services/weather";
import {
  getExchangeRates,
  getSupportedCurrencies,
  convertCurrency,
  formatCurrency,
} from "../services/currency";
import type { CurrencyInfo, ExchangeRatesResponse } from "../services/currency";
import {
  updateTrip,
  getTrip,
  checkFavorite,
  favoriteTrip,
  unfavoriteTrip,
  getTripNotes,
  addTripNote,
  deleteTripNote,
  getTripRating,
  rateTrip,
  downloadTripPdf,
  exportTrip,
  exportTripCalendar,
  importTrip,
  duplicateTrip,
  saveTripAsTemplate,
  replanActiveDay,
  addRouteStop,
  switchTransportMode,
  reallocateTripBudget,
  castGroupVote,
  resolveGroupConflicts,
  sendAssistantChatMessage,
  optimizeTrip,
  getAttractionAlternatives,
  executeAttractionAction,
  getPlaceDetails,
} from "../services/api";
import type { AlternativeAttraction, PlaceDetail } from "../services/api";



import type {
  Place,
  Traveler,
  TripResponse,
  Weather,
  Dashboard as DashboardType,
} from "../types/api";

import type { ExpenseResponse } from "../types/expense";


function getTripIdFromUrl(): string | undefined {
  if (typeof window === "undefined") {
    return undefined;
  }

  const match = window.location.pathname.match(
    /\/trip\/([^/]+)/
  );

  return match?.[1];
}


export default function TripView() {
  const [editPrompt, setEditPrompt] = useState("");
  const [updating, setUpdating] = useState(false);

  const navigate = useNavigate();

  const [selectedPlace, setSelectedPlace] =
    useState<Place | null>(null);

  const tripId = getTripIdFromUrl();

  const [isFavorite, setIsFavorite] =
    useState(false);
  const [notes, setNotes] = useState<string[]>([]);
  const [newNote, setNewNote] = useState("");
  const [data, setData] =
    useState<TripResponse | null>(null);

  const [expenseData, setExpenseData] =
    useState<ExpenseResponse | null>(null);
  const [tripRating, setTripRating] = useState<number | null>(null);
  const [ratingFeedback, setRatingFeedback] = useState("");
  const [ratingSaved, setRatingSaved] = useState(false);
  const [showShareModal, setShowShareModal] = useState(false);
  const userRole = data?.role || "owner";
  const isViewer = userRole === "viewer";
  const importFileInputRef = useRef<HTMLInputElement>(null);

  const handleQuickImportFile = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    const reader = new FileReader();
    reader.onload = async (event) => {
      try {
        const text = event.target?.result as string;
        const parsed = JSON.parse(text);
        const res = await importTrip(parsed);
        alert(`Trip restored successfully! ID: ${res.trip_id}`);
        navigate(`/trip/${res.trip_id}`);
      } catch (err: any) {
        alert(
          err instanceof SyntaxError
            ? "Malformed JSON: invalid syntax"
            : err.message || "Failed to import trip"
        );
      }
    };
    reader.readAsText(file);
    e.target.value = "";
  };

  const [duplicating, setDuplicating] = useState(false);

  const handleDuplicateTrip = async () => {
    if (!tripId) return;
    try {
      setDuplicating(true);
      const res = await duplicateTrip(tripId);
      alert(`Trip duplicated successfully! New ID: ${res.trip_id}`);
      navigate(`/trip/${res.trip_id}`);
    } catch (err: any) {
      alert(err.message || "Failed to duplicate trip");
    } finally {
      setDuplicating(false);
    }
  };

  const [showTemplateModal, setShowTemplateModal] = useState(false);
  const [templateName, setTemplateName] = useState("");
  const [templateDesc, setTemplateDesc] = useState("");
  const [templateCategory, setTemplateCategory] = useState("General");
  const [savingTemplate, setSavingTemplate] = useState(false);

  const handleSaveAsTemplate = async () => {
    if (!tripId) return;
    try {
      setSavingTemplate(true);
      const res = await saveTripAsTemplate(
        tripId,
        templateName.trim() || undefined,
        templateDesc.trim() || undefined,
        templateCategory
      );
      alert(`Success! Template "${res.name}" created. You can reuse it anytime from the Templates tab.`);
      setShowTemplateModal(false);
      setTemplateName("");
      setTemplateDesc("");
    } catch (err: any) {
      alert(err.message || "Failed to create template from trip");
    } finally {
      setSavingTemplate(false);
    }
  };

  // Real-time day replanning state
  const [showReplanModal, setShowReplanModal] = useState(false);
  const [replanTargetDay, setReplanTargetDay] = useState(1);
  const [replanCompletedAttractions, setReplanCompletedAttractions] = useState<string[]>([]);
  const [replanRemainingHours, setReplanRemainingHours] = useState(4.0);
  const [replanCurrentLocName, setReplanCurrentLocName] = useState("");
  const [replanLoading, setReplanLoading] = useState(false);

  const handleOpenReplan = (dayStr: string) => {
    const dNum = parseInt(dayStr) || 1;
    setReplanTargetDay(dNum);
    const dayPlaces = (data?.trip as any)?.day_schedule?.[dayStr] || [];
    const completed = dayPlaces.filter((p: any) => p.is_completed).map((p: any) => p.name);
    setReplanCompletedAttractions(completed);
    setReplanCurrentLocName("");
    setReplanRemainingHours(4.0);
    setShowReplanModal(true);
  };

  const handleExecuteReplan = async () => {
    if (!tripId) return;
    try {
      setReplanLoading(true);
      const res = await replanActiveDay(tripId, {
        day: replanTargetDay,
        completed_attractions: replanCompletedAttractions,
        remaining_hours: replanRemainingHours,
        current_location_name: replanCurrentLocName.trim() || undefined,
      });

      if (res.trip) {
        setData((prev) => prev ? { ...prev, trip: res.trip } : null);
      }
      alert(res.audit?.summary || "Day successfully replanned!");
      setShowReplanModal(false);
    } catch (err: any) {
      alert(err.message || "Failed to replan day");
    } finally {
      setReplanLoading(false);
    }
  };

  const [addingRouteStopId, setAddingRouteStopId] = useState<string | null>(null);
  const [selectedRouteStopDay, setSelectedRouteStopDay] = useState<{ [stopId: string]: number }>({});
  const [routeStopFeedback, setRouteStopFeedback] = useState<string | null>(null);

  const handleInsertRouteStop = async (stop: any, dayNum: number) => {
    if (!tripId) return;

    // Check if the stop already exists on the selected day
    const existingStops = (trip?.day_schedule as any)?.[String(dayNum)] || [];
    const isDuplicate = existingStops.some((s: any) =>
      s.name?.toLowerCase().trim() === stop.name?.toLowerCase().trim()
    );

    let allowRepeat = false;
    if (isDuplicate) {
      const confirmAdd = window.confirm(
        `"${stop.name}" is already scheduled on Day ${dayNum}. Would you like to add it anyway?`
      );
      if (!confirmAdd) return;
      allowRepeat = true;
    }

    setAddingRouteStopId(stop.id || stop.name);
    setRouteStopFeedback(null);
    try {
      const res = await addRouteStop(tripId, dayNum, stop, allowRepeat);
      if (res.trip) {
        setData((prev) => (prev ? { ...prev, trip: res.trip, dashboard: res.trip.dashboard || prev.dashboard } : null));
        setRouteStopFeedback(res.audit?.summary || `Added ${stop.name} to Day ${dayNum}`);
      }
    } catch (err: any) {
      alert(err.message || "Failed to add route stop");
    } finally {
      setAddingRouteStopId(null);
    }
  };

  const [switchingTransport, setSwitchingTransport] = useState(false);
  const [transportStatusMessage, setTransportStatusMessage] = useState<string | null>(null);

  const handleSwitchTransport = async (newMode: string) => {
    if (!tripId || switchingTransport) return;
    try {
      setSwitchingTransport(true);
      setTransportStatusMessage(null);
      const res = await switchTransportMode(tripId, newMode);
      if (res.trip) {
        setData((prev) => (prev ? { ...prev, trip: res.trip, dashboard: res.trip.dashboard || prev.dashboard } : null));
        setTransportStatusMessage(res.audit?.summary || `Switched transport to ${newMode.toUpperCase()}`);
      }
    } catch (err: any) {
      alert(err.message || "Failed to switch transport mode");
    } finally {
      setSwitchingTransport(false);
    }
  };

  const [selectedBudgetStrategy, setSelectedBudgetStrategy] = useState("conservative");
  const [reallocatingBudget, setReallocatingBudget] = useState(false);
  const [budgetReallocFeedback, setBudgetReallocFeedback] = useState<string | null>(null);

  const handleApplyBudgetReallocation = async (strategy: string) => {
    if (!tripId || reallocatingBudget) return;
    try {
      setReallocatingBudget(true);
      setBudgetReallocFeedback(null);
      const res = await reallocateTripBudget(tripId, strategy);
      if (res.trip) {
        setData((prev) => (prev ? { ...prev, trip: res.trip, dashboard: res.trip.dashboard || prev.dashboard } : null));
        setBudgetReallocFeedback(res.audit?.summary || "Budget reallocated successfully!");
      }
    } catch (err: any) {
      alert(err.message || "Failed to reallocate budget");
    } finally {
      setReallocatingBudget(false);
    }
  };

  const [votingTraveler, setVotingTraveler] = useState("");
  const [votingLoading, setVotingLoading] = useState(false);
  const [resolvingConflicts, setResolvingConflicts] = useState(false);
  const [groupConflictFeedback, setGroupConflictFeedback] = useState<string | null>(null);

  const handleCastVote = async (attractionName: string, vote: string) => {
    if (!tripId || votingLoading) return;
    const voter = votingTraveler || (trip?.travelers?.[0]?.name) || "Traveler";
    try {
      setVotingLoading(true);
      setGroupConflictFeedback(null);
      const res = await castGroupVote(tripId, voter, attractionName, vote);
      if (res.trip) {
        setData((prev) => (prev ? { ...prev, trip: res.trip, dashboard: res.trip.dashboard || prev.dashboard } : null));
        setGroupConflictFeedback(res.audit?.summary || `Vote recorded for ${attractionName}!`);
      }
    } catch (err: any) {
      alert(err.message || "Failed to submit vote");
    } finally {
      setVotingLoading(false);
    }
  };

  const handleResolveConflicts = async () => {
    if (!tripId || resolvingConflicts) return;
    try {
      setResolvingConflicts(true);
      setGroupConflictFeedback(null);
      const res = await resolveGroupConflicts(tripId);
      if (res.trip) {
        setData((prev) => (prev ? { ...prev, trip: res.trip, dashboard: res.trip.dashboard || prev.dashboard } : null));
        setGroupConflictFeedback(res.audit?.summary || "Conflicts resolved into fair compromise!");
      }
    } catch (err: any) {
      alert(err.message || "Failed to resolve conflicts");
    } finally {
      setResolvingConflicts(false);
    }
  };

  // Step 59: AI Assistant Copilot State
  const [chatOpen, setChatOpen] = useState(false);
  const [chatInput, setChatInput] = useState("");
  const [chatLoading, setChatLoading] = useState(false);
  const [chatMessages, setChatMessages] = useState<Array<{ role: "user" | "assistant"; text: string }>>([
    {
      role: "assistant",
      text: "Hi! I am your TravelSync AI Copilot. Ask me about your itinerary, weather advice, packing tips, or route alternatives!",
    },
  ]);
  const [chatSuggestions, setChatSuggestions] = useState<string[]>([
    "What should I pack for this trip?",
    "Where should I eat lunch?",
    "What is the best time to visit top spots?",
    "Give me an overview of today schedule",
  ]);

  const handleSendChatMessage = async (msgToSend?: string) => {
    const text = (msgToSend !== undefined ? msgToSend : chatInput).trim();
    if (!text || !tripId || chatLoading) return;
    setChatMessages((prev) => [...prev, { role: "user", text }]);
    if (msgToSend === undefined) setChatInput("");
    try {
      setChatLoading(true);
      const res = await sendAssistantChatMessage(tripId, text);
      if (res && res.reply) {
        setChatMessages((prev) => [...prev, { role: "assistant", text: res.reply }]);
        if (res.suggested_actions && res.suggested_actions.length > 0) {
          setChatSuggestions(res.suggested_actions);
        }
        if (res.trip) {
          setData((prev) => (prev ? { ...prev, trip: res.trip, dashboard: res.trip.dashboard || prev.dashboard } : null));
        }
      }
    } catch (err: any) {
      setChatMessages((prev) => [
        ...prev,
        { role: "assistant", text: "Sorry, could not reach the assistant: " + err.message },
      ]);
    } finally {
      setChatLoading(false);
    }
  };

  // Step 60: AI Trip Optimization State
  const [optimizingTrip, setOptimizingTrip] = useState(false);
  const [optimizationAudit, setOptimizationAudit] = useState<any>(null);
  const [showOptDiffModal, setShowOptDiffModal] = useState(false);

  const handleExecuteOptimization = async () => {
    if (!tripId || optimizingTrip) return;
    try {
      setOptimizingTrip(true);
      const res = await optimizeTrip(tripId);
      if (res.trip) {
        setData((prev) => (prev ? { ...prev, trip: res.trip, dashboard: res.trip.dashboard || prev.dashboard } : null));
        setOptimizationAudit(res.audit);
      }
    } catch (err: any) {
      alert(err.message || "Failed to optimize trip");
    } finally {
      setOptimizingTrip(false);
    }
  };

  // Step 70: Attraction Remove / Replace State
  const [attractionActionModal, setAttractionActionModal] = useState<{
    open: boolean;
    mode: "choice" | "replace";
    day: string;
    place: Place | null;
  }>({
    open: false,
    mode: "choice",
    day: "",
    place: null,
  });

  const [alternativesLoading, setAlternativesLoading] = useState(false);
  const [alternativesList, setAlternativesList] = useState<AlternativeAttraction[]>([]);
  const [alternativesError, setAlternativesError] = useState<string | null>(null);
  const [actionExecuting, setActionExecuting] = useState(false);
  const [attractionActionMessage, setAttractionActionMessage] = useState<{ type: "success" | "error"; text: string } | null>(null);

  const fetchAlternatives = async (day: string, placeName: string) => {
    if (!tripId) return;
    try {
      setAlternativesLoading(true);
      setAlternativesError(null);
      const res = await getAttractionAlternatives(tripId, day, placeName);
      setAlternativesList(res.alternatives || []);
    } catch (err: any) {
      setAlternativesError(err.message || "Failed to load alternative attractions");
      setAlternativesList([]);
    } finally {
      setAlternativesLoading(false);
    }
  };

  const handleOpenRemoveAttraction = (day: string, place: Place) => {
    setAttractionActionMessage(null);
    setAlternativesError(null);
    setAlternativesList([]);
    setAttractionActionModal({
      open: true,
      mode: "choice",
      day,
      place,
    });
  };

  const handleOpenReplaceAttraction = async (day: string, place: Place) => {
    setAttractionActionMessage(null);
    setAlternativesError(null);
    setAttractionActionModal({
      open: true,
      mode: "replace",
      day,
      place,
    });
    await fetchAlternatives(day, place.name);
  };

  const handleExecuteKeepEmpty = async () => {
    const { day, place } = attractionActionModal;
    if (!tripId || !place || !day || actionExecuting) return;

    try {
      setActionExecuting(true);
      const res = await executeAttractionAction(tripId, day, place.name, "remove");
      if (res.trip) {
        setData((prev) => (prev ? { ...prev, trip: res.trip, dashboard: res.trip.dashboard || prev.dashboard } : null));
      }
      setAttractionActionMessage({
        type: "success",
        text: res.message || `Removed "${place.name}" from Day ${day} (slot kept empty).`,
      });
      setAttractionActionModal({ open: false, mode: "choice", day: "", place: null });
    } catch (err: any) {
      setAttractionActionMessage({
        type: "error",
        text: err.message || `Failed to remove "${place.name}". Itinerary preserved.`,
      });
    } finally {
      setActionExecuting(false);
    }
  };

  const handleExecuteReplace = async (replacement: AlternativeAttraction) => {
    const { day, place } = attractionActionModal;
    if (!tripId || !place || !day || actionExecuting) return;

    try {
      setActionExecuting(true);
      const res = await executeAttractionAction(tripId, day, place.name, "replace", replacement);
      if (res.trip) {
        setData((prev) => (prev ? { ...prev, trip: res.trip, dashboard: res.trip.dashboard || prev.dashboard } : null));
      }
      setAttractionActionMessage({
        type: "success",
        text: res.message || `Replaced "${place.name}" with "${replacement.name}" on Day ${day}.`,
      });
      setAttractionActionModal({ open: false, mode: "choice", day: "", place: null });
    } catch (err: any) {
      setAttractionActionMessage({
        type: "error",
        text: err.message || `Failed to replace "${place.name}". Itinerary preserved.`,
      });
    } finally {
      setActionExecuting(false);
    }
  };

  // Step 71: Place Information Detail Modal State
  const [placeDetailModal, setPlaceDetailModal] = useState<{
    isOpen: boolean;
    initialPlace: any;
    details: PlaceDetail | null;
    loading: boolean;
    error: string | null;
  }>({
    isOpen: false,
    initialPlace: null,
    details: null,
    loading: false,
    error: null,
  });

  const handleShowPlaceInfo = async (place: any) => {
    if (!place || !place.name) return;
    setPlaceDetailModal({
      isOpen: true,
      initialPlace: place,
      details: null,
      loading: true,
      error: null,
    });

    try {
      const placeType = place.place_type || (place.category?.toLowerCase().includes("hotel") ? "hotel" : "attraction");
      const res = await getPlaceDetails(
        place.name,
        placeType,
        place.category,
        place.lat,
        place.lon
      );
      if (res.details) {
        setPlaceDetailModal((prev) => ({
          ...prev,
          details: res.details,
          loading: false,
        }));
      }
    } catch (err: any) {
      setPlaceDetailModal((prev) => ({
        ...prev,
        loading: false,
        error: err.message || "Failed to load additional place details",
      }));
    }
  };

  // Step 73: Live Currency Conversion State
  const [selectedCurrency, setSelectedCurrency] = useState<string>("INR");
  const [supportedCurrencies, setSupportedCurrencies] = useState<Record<string, CurrencyInfo>>({});
  const [ratesData, setRatesData] = useState<ExchangeRatesResponse | null>(null);
  const [currencyLoading, setCurrencyLoading] = useState<boolean>(false);
  const [currencyError, setCurrencyError] = useState<string | null>(null);

  useEffect(() => {
    let mounted = true;
    async function initCurrencies() {
      setCurrencyLoading(true);
      try {
        const [suppRes, ratesRes] = await Promise.allSettled([
          getSupportedCurrencies(),
          getExchangeRates("USD"),
        ]);
        if (mounted) {
          if (suppRes.status === "fulfilled") {
            setSupportedCurrencies(suppRes.value.currencies || {});
          }
          if (ratesRes.status === "fulfilled") {
            setRatesData(ratesRes.value);
            setCurrencyError(null);
          } else {
            setCurrencyError("Live exchange rates unavailable");
          }
        }
      } catch (err: any) {
        if (mounted) {
          setCurrencyError(err.message || "Failed to load currency rates");
        }
      } finally {
        if (mounted) {
          setCurrencyLoading(false);
        }
      }
    }
    initCurrencies();
    return () => {
      mounted = false;
    };
  }, []);

  const formatTripAmount = (amount: number, itemCurrency = trip?.budget?.currency || "INR") => {
    const src = itemCurrency || "INR";
    if (!ratesData?.rates || selectedCurrency === src) {
      return formatCurrency(amount, selectedCurrency);
    }
    const converted = convertCurrency(amount, src, selectedCurrency, ratesData.rates);
    return formatCurrency(converted, selectedCurrency);
  };

  // Step 74: Live Weather Forecasts & Disruption Alerts State
  const [weatherAlertsData, setWeatherAlertsData] = useState<TripWeatherAlertsResponse | null>(null);
  const [weatherLoading, setWeatherLoading] = useState<boolean>(false);
  const [weatherError, setWeatherError] = useState<string | null>(null);

  useEffect(() => {
    if (!tripId) return;
    let mounted = true;
    async function loadWeather() {
      setWeatherLoading(true);
      try {
        const res = await getTripWeatherAlerts(tripId);
        if (mounted) {
          setWeatherAlertsData(res);
          setWeatherError(null);
        }
      } catch (err: any) {
        if (mounted) {
          setWeatherError(err.message || "Failed to load live weather alerts");
        }
      } finally {
        if (mounted) {
          setWeatherLoading(false);
        }
      }
    }
    loadWeather();
    return () => {
      mounted = false;
    };
  }, [tripId]);




  /*
   * Check whether this trip is already a favorite.
   */
  useEffect(() => {
    if (!tripId) return;

    checkFavorite(tripId)
      .then(setIsFavorite)
      .catch(() => {});
  }, [tripId]);


  /*
   * Load trip and expense data.
   */
  useEffect(() => {
    const id = getTripIdFromUrl();

    if (!id) return;

    async function fetchTrip(tripId: string) {
      try {
        const json: TripResponse =
          await getTrip(tripId);

        setData(json);

        const expenses =
          await getExpenses(tripId);

        setExpenseData(expenses);
        const savedNotes =
  await getTripNotes(tripId);
  

setNotes(savedNotes);
const savedRating =
  await getTripRating(tripId);

if (savedRating) {
  setTripRating(savedRating.rating);
  setRatingFeedback(savedRating.feedback);
}
      } catch (err) {
        console.error(err);
      }
    }

    fetchTrip(id);
  }, []);


  /*
   * All hooks must be above this conditional return.
   */
  if (!tripId) {
    return <p>Trip ID not found</p>;
  }


  const handleTripEdit = async () => {
    if (!editPrompt.trim()) {
      return;
    }

    try {
      setUpdating(true);

      const updatedTrip =
        await updateTrip(
          tripId,
          editPrompt
        );

      setData(updatedTrip);
      setEditPrompt("");

    } catch (error) {
      console.error(
        "Trip update failed:",
        error
      );
    } finally {
      setUpdating(false);
    }
  };


  
    async function handleAddExpense(
  title: string,
  amount: number,
  paidBy: string
) {if (!tripId) {
    return;
  }


  await addExpense(tripId, {
    title,
    amount,
    paid_by: paidBy,
  });

  const updated = await getExpenses(tripId);

  setExpenseData(updated);
}


  async function handleRegenerateDay(
    day: string
  ) {
    try {
      const updatedTrip: TripResponse =
        await updateTrip(
          tripId,
          `Regenerate Day ${day}`
        );

      setData(updatedTrip);

    } catch (error) {
      console.error(
        "Regeneration failed:",
        error
      );
    }
  }


  if (!data) {
    return <div>Loading...</div>;
  }


  const rawTrip = (data as any)?.trip ?? (data as any);
  const trip: TripResponse["trip"] & Record<string, any> = {
    ...rawTrip,
    destination: rawTrip?.destination ?? "Trip",
    source: rawTrip?.source ?? "",
    start_date: rawTrip?.start_date ?? "",
    end_date: rawTrip?.end_date ?? "",
    destination_location: rawTrip?.destination_location ?? { lat: 0, lon: 0 },
    budget: {
      total: typeof rawTrip?.budget?.total === "number" ? rawTrip.budget.total : 0,
      total_budget: typeof rawTrip?.budget?.total_budget === "number" ? rawTrip.budget.total_budget : (rawTrip?.budget?.total || 0),
      estimated_cost: typeof rawTrip?.budget?.estimated_cost === "number" ? rawTrip.budget.estimated_cost : 0,
      remaining: typeof rawTrip?.budget?.remaining === "number" ? rawTrip.budget.remaining : (rawTrip?.budget?.total || 0),
      average_per_day: typeof rawTrip?.budget?.average_per_day === "number" ? rawTrip.budget.average_per_day : 0,
      average_per_person: typeof rawTrip?.budget?.average_per_person === "number" ? rawTrip.budget.average_per_person : 0,
      currency: rawTrip?.budget?.currency || "INR",
      status: rawTrip?.budget?.status || "Within Budget",
      breakdown: rawTrip?.budget?.breakdown || {},
      categories: rawTrip?.budget?.categories || { hotel: 0, food: 0, transport: 0, activities: 0, emergency: 0 },
      per_person: Array.isArray(rawTrip?.budget?.per_person) ? rawTrip.budget.per_person : [],
      ...(typeof rawTrip?.budget === "object" && rawTrip?.budget !== null ? rawTrip.budget : {}),
    },
    weather: Array.isArray(rawTrip?.weather) ? rawTrip.weather : [],
    hotels: Array.isArray(rawTrip?.hotels) ? rawTrip.hotels : [],
    places: Array.isArray(rawTrip?.places) ? rawTrip.places : [],
    day_schedule: rawTrip?.day_schedule ?? {},
    route_coordinates: Array.isArray(rawTrip?.route_coordinates) ? rawTrip.route_coordinates : [],
    travelers: Array.isArray(rawTrip?.travelers) ? rawTrip.travelers : [],
    traveler_conflicts: Array.isArray(rawTrip?.traveler_conflicts) ? rawTrip.traveler_conflicts : [],
    transport: rawTrip?.transport ?? {
      mode: rawTrip?.travel_mode || "car",
      label: "Road Trip",
      description: "Direct travel",
      distance_km: 0,
      duration_hours: 0,
      legs: [],
    },
  };

  const rawDashboard = (data as any)?.dashboard ?? (data as any)?.trip?.dashboard;
  const dashboard: DashboardType = rawDashboard ?? {
    source: trip.source || "Origin",
    destination: trip.destination || "Destination",
    days: 1,
    travel_mode: trip.transport?.mode || trip.travel_mode || "car",
    weather: trip.weather?.[0]?.description || "Clear",
    hotel_count: trip.hotels?.length || 0,
    attraction_count: trip.places?.length || 0,
    mandatory_count: 0,
    total_activities: trip.places?.length || 0,
    activities_per_day: trip.places?.length || 0,
    distance: trip.transport?.distance_km || 0,
    duration: trip.transport?.duration_hours || 0,
    budget: typeof trip.budget?.total === "number" ? trip.budget.total : (trip.budget?.total_budget || 0),
    estimated_cost: 0,
    remaining: typeof trip.budget?.total === "number" ? trip.budget.total : 0,
    budget_status: "Within Budget",
    hotel_cost: 0,
    food_cost: 0,
    transport_cost: 0,
    activity_cost: 0,
    emergency_cost: 0,
    average_per_day: 0,
    average_per_person: 0,
  };

  const normalizedWeather: Weather[] = Array.isArray(trip.weather)
    ? trip.weather.map((w) => ({
        ...w,
        description: w.description ?? "",
      }))
    : [];

  const isMulti = (trip as any)?.is_multi_destination || ((trip as any)?.destinations && (trip as any).destinations.length > 1);
  const destinationsList = (trip as any)?.destinations || [];

  const travelLegs = (trip as any)?.inter_destination_travel || [];
  const constraintAnalysis = (trip as any)?.constraint_analysis;
  const weatherReplanning = (trip as any)?.weather_replanning;
  const routeAttractions: any[] = (trip as any)?.route_attractions || [];
  const transportRecs = (trip as any)?.transport_recommendations;
  const budgetRealloc = (trip as any)?.budget_reallocation || (trip?.budget ? {
    active_strategy: "conservative",
    strategy_label: "Conservative & Balanced",
    strategy_description: "Preserves a 10% emergency buffer while securing reliable lodging and steady meals.",
    available_strategies: [
      { id: "conservative", label: "Conservative & Balanced", description: "Preserves a 10% emergency buffer while securing reliable lodging and steady meals." },
      { id: "experience", label: "Experience Maximizer", description: "Funnels savings from lodging and transit into top attractions, tours, and culinary memories." },
      { id: "cost_saver", label: "Cost Saver / High Reserve", description: "Minimizes non-essential overhead and retains an 18% reserve for shopping and unexpected savings." },
    ],
    categories: {
      hotel: { current_amount: trip.budget.categories?.hotel || 0, proposed_amount: Math.round((trip.budget.total_budget || trip.budget.estimated_cost || 20000) * 0.38), delta_amount: 0, current_percentage: 38, target_percentage: 38 },
      food: { current_amount: trip.budget.categories?.food || 0, proposed_amount: Math.round((trip.budget.total_budget || trip.budget.estimated_cost || 20000) * 0.25), delta_amount: 0, current_percentage: 25, target_percentage: 25 },
      transport: { current_amount: trip.budget.categories?.transport || 0, proposed_amount: Math.round((trip.budget.total_budget || trip.budget.estimated_cost || 20000) * 0.17), delta_amount: 0, current_percentage: 17, target_percentage: 17 },
      activities: { current_amount: trip.budget.categories?.activities || 0, proposed_amount: Math.round((trip.budget.total_budget || trip.budget.estimated_cost || 20000) * 0.10), delta_amount: 0, current_percentage: 10, target_percentage: 10 },
      emergency: { current_amount: trip.budget.categories?.emergency || 0, proposed_amount: Math.round((trip.budget.total_budget || trip.budget.estimated_cost || 20000) * 0.10), delta_amount: 0, current_percentage: 10, target_percentage: 10 },
    },
    trade_off_suggestions: [
      { action: "Optimize lodging buffer", impact: "Funnels savings from lodging into top attractions and tours without raising total spend." }
    ],
  } : null);
  const groupDecisions = (trip as any)?.group_decisions;
  const optimizationScore = (trip as any)?.optimization_score;






  return (
    <div className="page-container">

      <button
        type="button"
        className="plan-another-button"
        onClick={() =>
          navigate("/", {
            state: {
              trip: trip,
            },
          })
        }
      >
        ← Plan Another Trip
      </button>

      {/* Sticky Section Quick-Navigation Bar */}
      <nav
        aria-label="Trip sections"
        style={{
          position: "sticky",
          top: 0,
          zIndex: 90,
          background: "rgba(255, 255, 255, 0.95)",
          backdropFilter: "blur(8px)",
          borderBottom: "1px solid #e2e8f0",
          padding: "10px 16px",
          margin: "0 -20px 20px -20px",
          display: "flex",
          gap: 8,
          overflowX: "auto",
          boxShadow: "0 2px 4px rgba(0,0,0,0.03)",
        }}
      >
        {[
          { label: "Overview", href: "#section-overview" },
          { label: "Itinerary", href: "#section-itinerary" },
          { label: "Route Discovery", href: "#section-route-discovery" },
          { label: "Budget Planner", href: "#section-budget" },
          { label: "Transport", href: "#section-transport" },
          { label: "Group Decisions", href: "#section-group-decisions" },
          { label: "Insights", href: "#section-insights" },
          { label: "AI Optimization", href: "#section-ai-optimization" },
        ].map((item) => (
          <a
            key={item.href}
            href={item.href}
            style={{
              fontSize: "0.82rem",
              fontWeight: 600,
              color: "#475569",
              textDecoration: "none",
              padding: "6px 14px",
              borderRadius: 20,
              background: "#f1f5f9",
              whiteSpace: "nowrap",
              transition: "all 0.2s ease",
            }}
          >
            {item.label}
          </a>
        ))}
      </nav>

      <div id="section-overview">
        <Dashboard dashboard={dashboard} />
      </div>


      {/* Role Badge & Collaboration Share */}
      <div style={{ display: "inline-flex", alignItems: "center", gap: 10, margin: "8px 0" }}>
        <span
          style={{
            padding: "6px 14px",
            borderRadius: "20px",
            fontSize: "0.85rem",
            fontWeight: 700,
            backgroundColor: userRole === "owner" ? "#fef3c7" : userRole === "editor" ? "#dbeafe" : "#f1f5f9",
            color: userRole === "owner" ? "#92400e" : userRole === "editor" ? "#1e40af" : "#475569",
            display: "inline-flex",
            alignItems: "center",
            gap: 4,
            border: "1px solid rgba(0,0,0,0.06)",
          }}
        >
          {userRole === "owner" ? "👑 Trip Owner" : userRole === "editor" ? "✏️ Editor" : "👁️ Viewer (Read Only)"}
        </span>

        {userRole === "owner" && (
          <button
            onClick={() => setShowShareModal(true)}
            style={{
              padding: "7px 16px",
              borderRadius: "8px",
              backgroundColor: "#4f46e5",
              color: "#fff",
              border: "none",
              fontWeight: 600,
              cursor: "pointer",
            }}
          >
            🔗 Share & Invite
          </button>
        )}
      </div>

      {isViewer && (
        <div
          style={{
            padding: "10px 16px",
            margin: "12px 0",
            backgroundColor: "#f8fafc",
            border: "1px solid #e2e8f0",
            borderRadius: "8px",
            color: "#475569",
            fontSize: "0.85rem",
            display: "flex",
            alignItems: "center",
            gap: 8,
          }}
        >
          ℹ️ <strong>View-only mode:</strong> You were invited as a viewer. You can explore the full itinerary, weather, and budget, but editing actions are disabled.
        </div>
      )}


      {/* Favorite Trip */}
      <button
        onClick={async () => {
          if (isFavorite) {
            await unfavoriteTrip(tripId);
            setIsFavorite(false);
          } else {
            await favoriteTrip(tripId);
            setIsFavorite(true);
          }
        }}
      >
        {isFavorite
          ? "★ Favorited"
          : "☆ Favorite"}
      </button>


      {/* Export Trip */}
      <button
        onClick={() => {
          if (tripId) {
            exportTrip(tripId);
          }
        }}
      >
        Export Trip
      </button>

      {/* Export to Calendar (.ics) */}
      <button
        className="export-calendar-btn"
        aria-label="Export itinerary to calendar (.ics)"
        onClick={() => {
          if (tripId) {
            exportTripCalendar(tripId);
          }
        }}
        title="Download .ics calendar file for Google Calendar, Apple Calendar, and Outlook"
      >
        📅 Export to Calendar
      </button>


      {/* Import Trip */}
      <input
        type="file"
        ref={importFileInputRef}
        accept=".json,application/json"
        style={{ display: "none" }}
        onChange={handleQuickImportFile}
      />
      <button
        onClick={() => {
          importFileInputRef.current?.click();
        }}
      >
        Import Trip
      </button>


      {/* Duplicate Trip */}
      <button
        onClick={handleDuplicateTrip}
        disabled={duplicating}
      >
        {duplicating ? "Duplicating..." : "Duplicate Trip"}
      </button>


      {/* Save as Template */}
      <button
        onClick={() => {
          if (dashboard) {
            setTemplateName(`${dashboard.days || 1}-Day ${dashboard.destination || "Trip"} Template`);
          }
          setShowTemplateModal(true);
        }}
      >
        Save as Template
      </button>


      {/* Compare Trip */}
      <button
        onClick={() => {
          if (tripId) {
            navigate(`/compare?trip1=${tripId}`);
          }
        }}
      >
        Compare Trip
      </button>

      {/* Trip Analytics & Insights */}
      <div id="section-insights">
        <TripInsightsCard tripId={tripId} />
      </div>

      {/* STEP 60: AI Trip Quality & Holistic Optimization Score Card */}
      {optimizationScore && (
        <div
          id="section-ai-optimization"
          style={{
            background: "#ffffff",
            borderRadius: 16,
            border: "1px solid #e0e7ff",
            boxShadow: "0 10px 25px -5px rgba(99, 102, 241, 0.1), 0 8px 10px -6px rgba(99, 102, 241, 0.05)",
            padding: 24,
            margin: "24px 0",
          }}
        >
          <div
            style={{
              display: "flex",
              justifyContent: "space-between",
              alignItems: "flex-start",
              flexWrap: "wrap",
              gap: 16,
              marginBottom: 20,
            }}
          >
            <div>
              <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                <h3 style={{ margin: 0, fontSize: "1.25rem", fontWeight: 800, color: "#1e1b4b" }}>
                  AI Trip Quality & Optimization Score
                </h3>
                <span
                  style={{
                    background: "linear-gradient(135deg, #4f46e5 0%, #7c3aed 100%)",
                    color: "#ffffff",
                    padding: "4px 12px",
                    borderRadius: 20,
                    fontSize: "0.78rem",
                    fontWeight: 700,
                    letterSpacing: "0.03em",
                  }}
                >
                  STEP 60 ENGINE
                </span>
              </div>
              <p style={{ margin: "6px 0 0 0", fontSize: "0.86rem", color: "#6b7280" }}>
                Holistic multi-variable quality audit evaluating transit efficiency, pacing, budget adherence, and group alignment.
              </p>
            </div>

            <div style={{ display: "flex", alignItems: "center", gap: 12, flexWrap: "wrap" }}>
              <div
                style={{
                  background: "linear-gradient(135deg, #e0e7ff 0%, #f5f3ff 100%)",
                  border: "2px solid #818cf8",
                  borderRadius: 16,
                  padding: "10px 18px",
                  textAlign: "center",
                }}
              >
                <div style={{ fontSize: "1.8rem", fontWeight: 900, color: "#3730a3", lineHeight: 1 }}>
                  {optimizationScore.overall_score}
                  <span style={{ fontSize: "0.9rem", fontWeight: 600, color: "#6366f1" }}>/100</span>
                </div>
                <div style={{ fontSize: "0.72rem", fontWeight: 700, color: "#4338ca", marginTop: 4, textTransform: "uppercase" }}>
                  {optimizationScore.tier_badge || "Optimized"}
                </div>
              </div>

              {((trip as any)?.optimization_comparison || optimizationAudit?.comparison) && (
                <button
                  type="button"
                  onClick={() => setShowOptDiffModal(true)}
                  style={{
                    background: "#ede9fe",
                    color: "#6d28d9",
                    border: "1px solid #c4b5fd",
                    borderRadius: 12,
                    padding: "12px 18px",
                    fontSize: "0.88rem",
                    fontWeight: 700,
                    cursor: "pointer",
                    display: "flex",
                    alignItems: "center",
                    gap: 6,
                    boxShadow: "0 2px 6px rgba(109, 40, 217, 0.12)",
                  }}
                >
                  What's Changed?
                </button>
              )}

              <button
                type="button"
                onClick={handleExecuteOptimization}
                disabled={optimizingTrip}
                style={{
                  background: "linear-gradient(135deg, #4f46e5 0%, #6366f1 100%)",
                  color: "#ffffff",
                  border: "none",
                  borderRadius: 12,
                  padding: "12px 20px",
                  fontSize: "0.9rem",
                  fontWeight: 700,
                  cursor: optimizingTrip ? "not-allowed" : "pointer",
                  opacity: optimizingTrip ? 0.7 : 1,
                  boxShadow: "0 4px 14px rgba(79, 70, 229, 0.35)",
                  display: "flex",
                  alignItems: "center",
                  gap: 8,
                }}
              >
                {optimizingTrip ? "Optimizing Itinerary..." : "One-Click AI Route Polish"}
              </button>
            </div>
          </div>

          {/* Audit banner if just executed */}
          {optimizationAudit && (
            <div
              style={{
                background: "#ecfdf5",
                border: "1px solid #6ee7b7",
                borderRadius: 12,
                padding: "12px 16px",
                marginBottom: 18,
                display: "flex",
                alignItems: "center",
                gap: 12,
              }}
            >
              <div style={{ flex: 1, fontSize: "0.86rem", color: "#065f46", fontWeight: 600 }}>
                {optimizationAudit.summary}
              </div>
            </div>
          )}

          {/* Metrics Breakdown */}
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))",
              gap: 14,
              marginBottom: 20,
            }}
          >
            <div style={{ background: "#f8fafc", borderRadius: 12, padding: "12px 14px", border: "1px solid #f1f5f9" }}>
              <div style={{ display: "flex", justifyContent: "space-between", fontSize: "0.8rem", color: "#475569", marginBottom: 6 }}>
                <span>Route Efficiency</span>
                <strong>{optimizationScore.metrics?.route_efficiency || 85}%</strong>
              </div>
              <div style={{ width: "100%", height: 6, background: "#e2e8f0", borderRadius: 3, overflow: "hidden" }}>
                <div
                  style={{
                    width: `${optimizationScore.metrics?.route_efficiency || 85}%`,
                    height: "100%",
                    background: "#4f46e5",
                    borderRadius: 3,
                  }}
                />
              </div>
            </div>

            <div style={{ background: "#f8fafc", borderRadius: 12, padding: "12px 14px", border: "1px solid #f1f5f9" }}>
              <div style={{ display: "flex", justifyContent: "space-between", fontSize: "0.8rem", color: "#475569", marginBottom: 6 }}>
                <span>Daily Pacing</span>
                <strong>{optimizationScore.metrics?.pacing_score || 85}%</strong>
              </div>
              <div style={{ width: "100%", height: 6, background: "#e2e8f0", borderRadius: 3, overflow: "hidden" }}>
                <div
                  style={{
                    width: `${optimizationScore.metrics?.pacing_score || 85}%`,
                    height: "100%",
                    background: "#0ea5e9",
                    borderRadius: 3,
                  }}
                />
              </div>
            </div>

            <div style={{ background: "#f8fafc", borderRadius: 12, padding: "12px 14px", border: "1px solid #f1f5f9" }}>
              <div style={{ display: "flex", justifyContent: "space-between", fontSize: "0.8rem", color: "#475569", marginBottom: 6 }}>
                <span>Budget Adherence</span>
                <strong>{optimizationScore.metrics?.budget_adherence || 90}%</strong>
              </div>
              <div style={{ width: "100%", height: 6, background: "#e2e8f0", borderRadius: 3, overflow: "hidden" }}>
                <div
                  style={{
                    width: `${optimizationScore.metrics?.budget_adherence || 90}%`,
                    height: "100%",
                    background: "#10b981",
                    borderRadius: 3,
                  }}
                />
              </div>
            </div>

            <div style={{ background: "#f8fafc", borderRadius: 12, padding: "12px 14px", border: "1px solid #f1f5f9" }}>
              <div style={{ display: "flex", justifyContent: "space-between", fontSize: "0.8rem", color: "#475569", marginBottom: 6 }}>
                <span>Traveler Alignment</span>
                <strong>{optimizationScore.metrics?.traveler_happiness || 88}%</strong>
              </div>
              <div style={{ width: "100%", height: 6, background: "#e2e8f0", borderRadius: 3, overflow: "hidden" }}>
                <div
                  style={{
                    width: `${optimizationScore.metrics?.traveler_happiness || 88}%`,
                    height: "100%",
                    background: "#f59e0b",
                    borderRadius: 3,
                  }}
                />
              </div>
            </div>
          </div>

          {/* Quick Stats Pill Grid */}
          <div
            style={{
              display: "flex",
              flexWrap: "wrap",
              gap: 12,
              background: "#f8fafc",
              padding: "12px 16px",
              borderRadius: 12,
              border: "1px solid #e2e8f0",
              marginBottom: 16,
            }}
          >
            <div style={{ fontSize: "0.82rem", color: "#334155" }}>
              <strong>Total Transit:</strong> {optimizationScore.stats?.total_transit_km || 0} km
            </div>
            <div style={{ color: "#cbd5e1" }}>|</div>
            <div style={{ fontSize: "0.82rem", color: "#334155" }}>
              <strong>Road Time:</strong> {optimizationScore.stats?.total_transit_minutes || 0} mins
            </div>
            <div style={{ color: "#cbd5e1" }}>|</div>
            <div style={{ fontSize: "0.82rem", color: "#334155" }}>
              <strong>Total Stops:</strong> {optimizationScore.stats?.total_places || 0} attractions
            </div>
            <div style={{ color: "#cbd5e1" }}>|</div>
            <div style={{ fontSize: "0.82rem", color: "#334155" }}>
              <strong>Duration:</strong> {optimizationScore.stats?.total_days || 0} day(s)
            </div>
          </div>

          {/* Recommendations */}
          {optimizationScore.recommendations?.length > 0 && (
            <div style={{ background: "#eff6ff", borderRadius: 10, padding: "10px 14px", border: "1px solid #bfdbfe" }}>
              <div style={{ fontSize: "0.78rem", fontWeight: 700, color: "#1e40af", textTransform: "uppercase", marginBottom: 4 }}>
                AI Polish Recommendations:
              </div>
              <ul style={{ margin: 0, paddingLeft: 18, fontSize: "0.82rem", color: "#1e3a8a" }}>
                {optimizationScore.recommendations.map((rec: string, rIdx: number) => (
                  <li key={rIdx}>{rec}</li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}

      {/* STEP 60: What's Changed AI Optimization Comparison Modal */}
      {showOptDiffModal && (() => {
        const comp = (trip as any)?.optimization_comparison || optimizationAudit?.comparison;
        if (!comp) return null;
        return (
          <div
            style={{
              position: "fixed",
              top: 0,
              left: 0,
              right: 0,
              bottom: 0,
              background: "rgba(15, 23, 42, 0.65)",
              backdropFilter: "blur(4px)",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              zIndex: 1100,
              padding: 20,
            }}
          >
            <div
              style={{
                background: "#ffffff",
                borderRadius: 16,
                padding: "24px 28px",
                maxWidth: 640,
                width: "100%",
                maxHeight: "85vh",
                overflowY: "auto",
                boxShadow: "0 25px 50px -12px rgba(0, 0, 0, 0.25)",
              }}
            >
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
                <h3 style={{ margin: 0, fontSize: "1.25rem", color: "#1e1b4b", display: "flex", alignItems: "center", gap: 8 }}>
                  AI Route Optimization Audit & Diff
                </h3>
                <button
                  type="button"
                  onClick={() => setShowOptDiffModal(false)}
                  style={{ background: "none", border: "none", fontSize: "1.2rem", cursor: "pointer", color: "#64748b" }}
                >
                  ✕
                </button>
              </div>

              {/* Metrics gain summary */}
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 10, marginBottom: 18 }}>
                <div style={{ background: "#f5f3ff", padding: "10px", borderRadius: 8, textAlign: "center" }}>
                  <div style={{ fontSize: "0.74rem", color: "#6b21a8" }}>Quality Score</div>
                  <strong style={{ fontSize: "1.1rem", color: "#581c87" }}>
                    {comp.initial_score} → {comp.optimized_score}
                  </strong>
                  <div style={{ fontSize: "0.7rem", color: "#16a34a", fontWeight: 700 }}>
                    +{comp.score_gain || 0} pts
                  </div>
                </div>

                <div style={{ background: "#ecfdf5", padding: "10px", borderRadius: 8, textAlign: "center" }}>
                  <div style={{ fontSize: "0.74rem", color: "#065f46" }}>Distance Saved</div>
                  <strong style={{ fontSize: "1.1rem", color: "#047857" }}>
                    {comp.distance_saved_km || 0} km
                  </strong>
                  <div style={{ fontSize: "0.7rem", color: "#059669" }}>
                    {comp.initial_total_transit_km || 0} → {comp.optimized_total_transit_km || 0} km
                  </div>
                </div>

                <div style={{ background: "#eff6ff", padding: "10px", borderRadius: 8, textAlign: "center" }}>
                  <div style={{ fontSize: "0.74rem", color: "#1e40af" }}>Transit Time Saved</div>
                  <strong style={{ fontSize: "1.1rem", color: "#1d4ed8" }}>
                    {comp.transit_minutes_saved || 0} mins
                  </strong>
                  <div style={{ fontSize: "0.7rem", color: "#2563eb" }}>
                    {comp.initial_transit_minutes || 0} → {comp.optimized_transit_minutes || 0} mins
                  </div>
                </div>
              </div>

              {/* Day-by-Day comparison */}
              <h4 style={{ margin: "0 0 10px", fontSize: "0.95rem", color: "#1e293b" }}>
                Day-by-Day Route Sequencing:
              </h4>
              <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
                {(comp.day_changes || []).map((dc: any, idx: number) => (
                  <div
                    key={idx}
                    style={{
                      border: "1px solid #e2e8f0",
                      borderRadius: 10,
                      padding: "12px 14px",
                      background: dc.has_reordering ? "#faf5ff" : "#f8fafc",
                    }}
                  >
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 8 }}>
                      <strong style={{ fontSize: "0.88rem", color: "#0f172a" }}>Day {dc.day}</strong>
                      <span
                        style={{
                          fontSize: "0.72rem",
                          fontWeight: 700,
                          padding: "2px 8px",
                          borderRadius: 12,
                          background: dc.has_reordering ? "#ede9fe" : "#f1f5f9",
                          color: dc.has_reordering ? "#6d28d9" : "#475569",
                        }}
                      >
                        {dc.has_reordering ? "✓ Reordered for minimum travel" : "Original sequence optimal"}
                      </span>
                    </div>

                    <div style={{ fontSize: "0.8rem", color: "#475569" }}>
                      <div style={{ marginBottom: 4 }}>
                        <span style={{ color: "#94a3b8", fontWeight: 600 }}>Initial: </span>
                        {(dc.initial_order || []).join("  →  ")}
                      </div>
                      <div>
                        <span style={{ color: "#7c3aed", fontWeight: 700 }}>Optimized: </span>
                        {(dc.optimized_order || []).join("  →  ")}
                      </div>
                    </div>
                  </div>
                ))}
              </div>

              <div style={{ display: "flex", justifyContent: "flex-end", marginTop: 20 }}>
                <button
                  type="button"
                  onClick={() => setShowOptDiffModal(false)}
                  style={{
                    padding: "8px 18px",
                    borderRadius: 8,
                    background: "#4f46e5",
                    color: "#ffffff",
                    border: "none",
                    fontWeight: 600,
                    cursor: "pointer",
                  }}
                >
                  Close
                </button>
              </div>
            </div>
          </div>
        );
      })()}


      {/* Multi-Destination Tour Route Card */}
      {isMulti && (
        <div
          style={{
            background: "#ffffff",
            border: "1px solid #e0e7ff",
            borderRadius: 12,
            padding: "20px 24px",
            margin: "24px 0",
            boxShadow: "0 4px 6px -1px rgba(79, 70, 229, 0.08)",
          }}
        >
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16, flexWrap: "wrap", gap: 10 }}>
            <div>
              <h3 style={{ margin: "0 0 4px", fontSize: "1.25rem", color: "#1e1b4b", display: "flex", alignItems: "center", gap: 8 }}>
                Multi-Destination Travel Circuit
              </h3>
              <p style={{ margin: 0, color: "#64748b", fontSize: "0.88rem" }}>
                Coordinated itinerary spanning {destinationsList.length} destinations
              </p>
            </div>
            <span
              style={{
                background: "#e0e7ff",
                color: "#4338ca",
                padding: "6px 14px",
                borderRadius: 20,
                fontSize: "0.82rem",
                fontWeight: 700,
              }}
            >
              {destinationsList.length} Cities • {dashboard.days} Days Total
            </span>
          </div>

          {/* Destinations Timeline / Steps */}
          <div style={{ display: "grid", gridTemplateColumns: `repeat(auto-fit, minmax(220px, 1fr))`, gap: 14, marginBottom: 20 }}>
            {destinationsList.map((stop: any, idx: number) => (
              <div
                key={idx}
                style={{
                  background: "#f8fafc",
                  border: "1px solid #e2e8f0",
                  borderRadius: 10,
                  padding: "14px",
                }}
              >
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 6 }}>
                  <span style={{ fontSize: "0.75rem", fontWeight: 700, color: "#4f46e5", textTransform: "uppercase" }}>
                    Stop {idx + 1}
                  </span>
                  <span style={{ background: "#ecfdf5", color: "#059669", fontSize: "0.78rem", fontWeight: 700, padding: "2px 8px", borderRadius: 10 }}>
                    Day {stop.start_day} - {stop.end_day} ({stop.days}d)
                  </span>
                </div>
                <div style={{ fontWeight: 700, color: "#0f172a", fontSize: "1.02rem", marginBottom: 4 }}>
                  {stop.name}
                </div>
                {stop.attraction_count !== undefined && (
                  <div style={{ fontSize: "0.8rem", color: "#64748b" }}>
                    {stop.attraction_count} attractions scheduled
                  </div>
                )}
              </div>
            ))}
          </div>

          {/* Travel Between Destinations Legs */}
          {travelLegs.length > 0 && (
            <div>
              <h4 style={{ margin: "0 0 10px", fontSize: "0.95rem", color: "#334155" }}>
                Inter-Destination Travel Legs
              </h4>
              <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                {travelLegs.map((leg: any, idx: number) => (
                  <div
                    key={idx}
                    style={{
                      background: "#f1f5f9",
                      borderRadius: 8,
                      padding: "10px 14px",
                      display: "flex",
                      justifyContent: "space-between",
                      alignItems: "center",
                      fontSize: "0.88rem",
                      flexWrap: "wrap",
                      gap: 8,
                    }}
                  >
                    <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                      <span style={{ fontWeight: 600, color: "#0f172a" }}>
                        Leg {leg.leg_index}: {leg.from_location?.split(",")[0]} -&gt; {leg.to_location?.split(",")[0]}
                      </span>
                    </div>
                    <div style={{ display: "flex", gap: 16, color: "#475569", fontSize: "0.82rem" }}>
                      <span>Distance: <strong>{leg.distance_km} km</strong></span>
                      <span>Duration: <strong>{leg.duration_hours} hrs</strong></span>
                      <span>Mode: <strong>{leg.travel_mode?.toUpperCase()}</strong></span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}


      <TravelerConflicts
        conflicts={trip.traveler_conflicts}
      />

      {/* Planning Constraints Audit Card */}
      {constraintAnalysis && (
        <div
          style={{
            background: "#ffffff",
            border: constraintAnalysis.violations?.length ? "1px solid #fecaca" : "1px solid #bbf7d0",
            borderRadius: 12,
            padding: "20px 24px",
            margin: "24px 0",
            boxShadow: "0 4px 6px -1px rgba(0, 0, 0, 0.05)",
          }}
        >
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 14, flexWrap: "wrap", gap: 10 }}>
            <div>
              <h3 style={{ margin: "0 0 4px", fontSize: "1.2rem", color: "#0f172a", display: "flex", alignItems: "center", gap: 8 }}>
                Planning Constraints Audit
              </h3>
              <p style={{ margin: 0, color: "#64748b", fontSize: "0.86rem" }}>
                Verified adherence to custom budget, distance limits, and location requirements
              </p>
            </div>
            <span
              style={{
                background: constraintAnalysis.violations?.length ? "#fee2e2" : "#dcfce7",
                color: constraintAnalysis.violations?.length ? "#991b1b" : "#166534",
                padding: "6px 14px",
                borderRadius: 20,
                fontSize: "0.82rem",
                fontWeight: 700,
              }}
            >
              {constraintAnalysis.violations?.length ? "Constraints Adjusted" : "✓ All Constraints Met"}
            </span>
          </div>

          {/* Satisfied items pills */}
          <div style={{ display: "flex", flexWrap: "wrap", gap: 8, marginBottom: 14 }}>
            {constraintAnalysis.satisfied?.budget !== undefined && (
              <span
                style={{
                  background: constraintAnalysis.satisfied.budget ? "#f0fdf4" : "#fef2f2",
                  color: constraintAnalysis.satisfied.budget ? "#15803d" : "#b91c1c",
                  border: `1px solid ${constraintAnalysis.satisfied.budget ? "#bbf7d0" : "#fecaca"}`,
                  padding: "4px 10px",
                  borderRadius: 16,
                  fontSize: "0.8rem",
                  fontWeight: 600,
                }}
              >
                {constraintAnalysis.satisfied.budget ? "✓ Budget Respected" : "✕ Budget Exceeded"}
              </span>
            )}
            {constraintAnalysis.satisfied?.distance !== undefined && (
              <span
                style={{
                  background: constraintAnalysis.satisfied.distance ? "#f0fdf4" : "#fef2f2",
                  color: constraintAnalysis.satisfied.distance ? "#15803d" : "#b91c1c",
                  border: `1px solid ${constraintAnalysis.satisfied.distance ? "#bbf7d0" : "#fecaca"}`,
                  padding: "4px 10px",
                  borderRadius: 16,
                  fontSize: "0.8rem",
                  fontWeight: 600,
                }}
              >
                {constraintAnalysis.satisfied.distance ? "✓ Daily Distance Capped" : "✕ Distance Exceeded"}
              </span>
            )}
            {constraintAnalysis.satisfied?.must_visit !== undefined && (
              <span
                style={{
                  background: constraintAnalysis.satisfied.must_visit ? "#f0fdf4" : "#fef2f2",
                  color: constraintAnalysis.satisfied.must_visit ? "#15803d" : "#b91c1c",
                  border: `1px solid ${constraintAnalysis.satisfied.must_visit ? "#bbf7d0" : "#fecaca"}`,
                  padding: "4px 10px",
                  borderRadius: 16,
                  fontSize: "0.8rem",
                  fontWeight: 600,
                }}
              >
                {constraintAnalysis.satisfied.must_visit ? "✓ Must-Visit Scheduled" : "✕ Must-Visit Missing"}
              </span>
            )}
            {constraintAnalysis.satisfied?.avoided_locations !== undefined && (
              <span
                style={{
                  background: constraintAnalysis.satisfied.avoided_locations ? "#f0fdf4" : "#fef2f2",
                  color: constraintAnalysis.satisfied.avoided_locations ? "#15803d" : "#b91c1c",
                  border: `1px solid ${constraintAnalysis.satisfied.avoided_locations ? "#bbf7d0" : "#fecaca"}`,
                  padding: "4px 10px",
                  borderRadius: 16,
                  fontSize: "0.8rem",
                  fontWeight: 600,
                }}
              >
                {constraintAnalysis.satisfied.avoided_locations ? "✓ Avoided Locations Excluded" : "✕ Avoided Visited"}
              </span>
            )}
          </div>

          {/* Details breakdown */}
          {constraintAnalysis.details && (
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))", gap: 10, fontSize: "0.85rem", background: "#f8fafc", padding: 12, borderRadius: 8, marginBottom: 12 }}>
              {constraintAnalysis.details.max_daily_distance_km && (
                <div>
                  <span style={{ color: "#64748b" }}>Daily Distance Limit: </span>
                  <strong>{constraintAnalysis.details.max_daily_distance_km} km</strong> (Peak: {constraintAnalysis.details.max_observed_day_distance_km} km)
                </div>
              )}
              {constraintAnalysis.details.max_budget && (
                <div>
                  <span style={{ color: "#64748b" }}>Budget Cap: </span>
                  <strong>${constraintAnalysis.details.max_budget}</strong> (Est: ${constraintAnalysis.details.estimated_total_cost})
                </div>
              )}
              {constraintAnalysis.details.must_visit_included?.length > 0 && (
                <div>
                  <span style={{ color: "#64748b" }}>Must-Visits Added: </span>
                  <strong>{constraintAnalysis.details.must_visit_included.join(", ")}</strong>
                </div>
              )}
              {constraintAnalysis.details.avoided_locations_excluded?.length > 0 && (
                <div>
                  <span style={{ color: "#64748b" }}>Locations Avoided: </span>
                  <strong>{constraintAnalysis.details.avoided_locations_excluded.join(", ")}</strong>
                </div>
              )}
            </div>
          )}

          {constraintAnalysis.explanation && (
            <div style={{ fontSize: "0.85rem", color: "#475569", fontStyle: "italic", borderTop: "1px solid #f1f5f9", paddingTop: 8 }}>
              Note: {constraintAnalysis.explanation}
            </div>
          )}

          {constraintAnalysis.violations?.length > 0 && (
            <div style={{ marginTop: 10, padding: "8px 12px", background: "#fef2f2", borderRadius: 6, border: "1px solid #fecaca" }}>
              <div style={{ fontSize: "0.82rem", fontWeight: 700, color: "#991b1b", marginBottom: 4 }}>Note on Constraints:</div>
              <ul style={{ margin: 0, paddingLeft: 18, fontSize: "0.82rem", color: "#b91c1c" }}>
                {constraintAnalysis.violations.map((v: string, i: number) => (
                  <li key={i}>{v}</li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}

      {/* Weather-Aware Replanning Alert Card */}
      {weatherReplanning && weatherReplanning.has_weather_replan && (
        <div
          style={{
            background: "#eff6ff",
            border: "1px solid #bfdbfe",
            borderRadius: 12,
            padding: "18px 22px",
            margin: "24px 0",
            boxShadow: "0 2px 4px rgba(37, 99, 235, 0.06)",
          }}
        >
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 12, flexWrap: "wrap", gap: 10 }}>
            <div>
              <h3 style={{ margin: "0 0 4px", fontSize: "1.18rem", color: "#1e3a8a", display: "flex", alignItems: "center", gap: 8 }}>
                Weather-Aware Itinerary Protection
              </h3>
              <p style={{ margin: 0, color: "#3b82f6", fontSize: "0.85rem" }}>
                {weatherReplanning.summary}
              </p>
            </div>
            <span
              style={{
                background: "#dbeafe",
                color: "#1d4ed8",
                padding: "4px 12px",
                borderRadius: 16,
                fontSize: "0.8rem",
                fontWeight: 700,
              }}
            >
              {weatherReplanning.decisions?.length || 0} Adjustments Made
            </span>
          </div>

          <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
            {weatherReplanning.decisions?.map((d: any, idx: number) => (
              <div
                key={idx}
                style={{
                  background: "#ffffff",
                  border: "1px solid #dbeafe",
                  borderRadius: 8,
                  padding: "10px 14px",
                  fontSize: "0.86rem",
                  color: "#1e293b",
                  display: "flex",
                  alignItems: "flex-start",
                  gap: 10,
                }}
              >
                <span style={{ fontSize: "0.8rem", fontWeight: 700, color: "#1e40af", padding: "2px 6px", background: "#dbeafe", borderRadius: 4 }}>
                  {d.condition?.toUpperCase() || "WEATHER"}
                </span>
                <div style={{ flex: 1 }}>
                  <div style={{ fontWeight: 600, color: "#1e40af" }}>
                    Day {d.day} ({d.date || "Forecast"}): {d.action === "swapped_activities" ? "Activity Rescheduled" : "Indoor Alternative Substituted"}
                  </div>
                  <div style={{ color: "#475569", marginTop: 2 }}>
                    {d.explanation}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Route-Aware Attraction Discovery Card */}
      {routeAttractions && routeAttractions.length > 0 && (
        <div
          id="section-route-discovery"
          style={{
            background: "#faf5ff",
            border: "1px solid #e9d5ff",
            borderRadius: 12,
            padding: "20px 24px",
            margin: "24px 0",
            boxShadow: "0 2px 6px rgba(147, 51, 234, 0.05)",
          }}
        >
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 14, flexWrap: "wrap", gap: 10 }}>
            <div>
              <h3 style={{ margin: "0 0 4px", fontSize: "1.2rem", color: "#6b21a8", display: "flex", alignItems: "center", gap: 8 }}>
                En-Route Sights & Scenic Waypoints
              </h3>
              <p style={{ margin: 0, color: "#9333ea", fontSize: "0.86rem" }}>
                Curated attractions along your corridor within easy detour distance. Seamlessly add stops to your daily itinerary!
              </p>
            </div>
            <span
              style={{
                background: "#f3e8ff",
                color: "#7e22ce",
                padding: "4px 12px",
                borderRadius: 16,
                fontSize: "0.82rem",
                fontWeight: 700,
              }}
            >
              {routeAttractions.length} Discovered Stops
            </span>
          </div>

          {routeStopFeedback && (
            <div
              style={{
                background: "#f0fdf4",
                border: "1px solid #bbf7d0",
                color: "#166534",
                padding: "8px 14px",
                borderRadius: 8,
                fontSize: "0.85rem",
                marginBottom: 14,
              }}
            >
              ✓ {routeStopFeedback}
            </div>
          )}

          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(320px, 1fr))", gap: 14 }}>
            {routeAttractions.map((stop: any, idx: number) => {
              const currentTargetDay = selectedRouteStopDay[stop.id || stop.name] || stop.recommended_day || 1;
              const isAdding = addingRouteStopId === (stop.id || stop.name);

              return (
                <div
                  key={stop.id || idx}
                  style={{
                    background: "#ffffff",
                    border: "1px solid #f3e8ff",
                    borderRadius: 10,
                    padding: "14px 16px",
                    display: "flex",
                    flexDirection: "column",
                    justifyContent: "space-between",
                    boxShadow: "0 1px 3px rgba(0,0,0,0.03)",
                  }}
                >
                  <div>
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: 8, marginBottom: 6 }}>
                      <strong style={{ color: "#1e293b", fontSize: "0.98rem" }}>{stop.name}</strong>
                      <div style={{ display: "flex", gap: 4, flexWrap: "wrap", justifyContent: "flex-end" }}>
                        {stop.recommended_day && (
                          <span
                            style={{
                              background: "#dcfce7",
                              color: "#166534",
                              padding: "2px 8px",
                              borderRadius: 12,
                              fontSize: "0.72rem",
                              fontWeight: 700,
                              whiteSpace: "nowrap",
                            }}
                          >
                            ★ Best Fit: Day {stop.recommended_day}
                          </span>
                        )}
                        <span
                          style={{
                            background: "#e0e7ff",
                            color: "#3730a3",
                            padding: "2px 8px",
                            borderRadius: 12,
                            fontSize: "0.72rem",
                            fontWeight: 600,
                            whiteSpace: "nowrap",
                          }}
                        >
                          {stop.corridor_position || `${stop.corridor_progress_percent}% along route`}
                        </span>
                      </div>
                    </div>

                    <div style={{ display: "flex", flexWrap: "wrap", gap: 6, marginBottom: 8 }}>
                      <span style={{ fontSize: "0.74rem", background: "#f1f5f9", padding: "2px 6px", borderRadius: 4, color: "#475569" }}>
                        {stop.category}
                      </span>
                      <span style={{ fontSize: "0.74rem", background: "#fef3c7", padding: "2px 6px", borderRadius: 4, color: "#92400e" }}>
                        +{stop.detour_distance_km} km detour
                      </span>
                      <span style={{ fontSize: "0.74rem", background: "#e0f2fe", padding: "2px 6px", borderRadius: 4, color: "#0369a1" }}>
                        +{stop.added_travel_time_minutes} min transit
                      </span>
                      <span style={{ fontSize: "0.74rem", background: "#ecfdf5", padding: "2px 6px", borderRadius: 4, color: "#065f46" }}>
                        ~{stop.recommended_pause_minutes} min pause
                      </span>
                    </div>

                    {stop.day_evaluations && (stop.day_evaluations[currentTargetDay] || stop.day_evaluations[String(currentTargetDay)]) && (() => {
                      const evalData = stop.day_evaluations[currentTargetDay] || stop.day_evaluations[String(currentTargetDay)];
                      const detourKm = evalData.detour_distance_km ?? evalData.detour_km ?? 0;
                      const routeKm = evalData.total_daily_route_km ?? evalData.day_route_km ?? 0;
                      const capacityOk = evalData.has_schedule_capacity ?? evalData.capacity_ok ?? true;
                      return (
                        <div
                          style={{
                            fontSize: "0.74rem",
                            background: "#fdf4ff",
                            border: "1px solid #f5d0fe",
                            color: "#86198f",
                            padding: "6px 10px",
                            borderRadius: 6,
                            marginBottom: 8,
                            lineHeight: 1.4,
                          }}
                        >
                          <div>
                            <strong>Day {currentTargetDay} Impact:</strong> +{detourKm} km detour | Route total: {routeKm} km{" "}
                            <span style={{ fontWeight: 600, color: capacityOk ? "#16a34a" : "#d97706" }}>
                              {capacityOk ? "(Capacity OK)" : "(Tight Schedule)"}
                            </span>
                          </div>
                          {evalData.distance_label && (
                            <div style={{ fontSize: "0.71rem", color: "#6b21a8", marginTop: 2 }}>
                              📍 {evalData.distance_label}
                            </div>
                          )}
                        </div>
                      );
                    })()}

                    <p style={{ margin: "0 0 10px", fontSize: "0.82rem", color: "#64748b", lineHeight: 1.4 }}>
                      {stop.description}
                    </p>
                  </div>

                  <div style={{ display: "flex", gap: 8, alignItems: "center", marginTop: 8, paddingTop: 8, borderTop: "1px dashed #f1f5f9" }}>
                    <label style={{ fontSize: "0.78rem", color: "#64748b", whiteSpace: "nowrap" }}>
                      Target Day:
                    </label>
                    <select
                      value={currentTargetDay}
                      onChange={(e) =>
                        setSelectedRouteStopDay((prev) => ({
                          ...prev,
                          [stop.id || stop.name]: parseInt(e.target.value) || 1,
                        }))
                      }
                      style={{
                        padding: "4px 8px",
                        fontSize: "0.8rem",
                        borderRadius: 6,
                        border: "1px solid #cbd5e1",
                        background: "#fff",
                      }}
                    >
                      {trip.day_schedule ? (
                        Object.keys(trip.day_schedule).map((d) => (
                          <option key={d} value={d}>
                            Day {d}
                          </option>
                        ))
                      ) : (
                        <option value={1}>Day 1</option>
                      )}
                    </select>

                    <button
                      type="button"
                      disabled={isAdding}
                      onClick={() => handleInsertRouteStop(stop, currentTargetDay)}
                      style={{
                        flex: 1,
                        padding: "5px 10px",
                        fontSize: "0.8rem",
                        fontWeight: 600,
                        background: isAdding ? "#94a3b8" : "#9333ea",
                        color: "#ffffff",
                        border: "none",
                        borderRadius: 6,
                        cursor: isAdding ? "default" : "pointer",
                        transition: "background 0.2s",
                      }}
                    >
                      {isAdding ? "Adding..." : "+ Add to Itinerary"}
                    </button>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      <div id="section-budget" className="section">

        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: 12, marginBottom: 16 }}>
          <h2 className="section-title" style={{ margin: 0 }}>
            Budget Overview
          </h2>
          <CurrencySelector
            selectedCurrency={selectedCurrency}
            onCurrencyChange={setSelectedCurrency}
            supportedCurrencies={supportedCurrencies}
            rateTimestamp={ratesData?.timestamp}
            isCached={ratesData?.is_cached}
            isFallback={ratesData?.is_fallback}
            isStale={ratesData?.is_stale}
            loading={currencyLoading}
            error={currencyError}
          />
        </div>

        <BudgetCard
          budget={trip.budget}
          displayCurrency={selectedCurrency}
          originalCurrency={trip.budget?.currency || "INR"}
          formatAmount={(amt) => formatTripAmount(amt, trip.budget?.currency || "INR")}
        />

        <BudgetStatus
          status={trip.budget.status}
          remaining={trip.budget.remaining}
        />

        <BudgetBreakdown
          categories={trip.budget.categories}
        />

        <BudgetPieChart
          categories={trip.budget.categories}
        />

        {/* Smart Budget Reallocation & Optimization Card */}
        {budgetRealloc && (
          <div
            style={{
              background: "#fffbeb",
              border: "1px solid #fde68a",
              borderRadius: 12,
              padding: "20px 24px",
              marginTop: 20,
              boxShadow: "0 2px 6px rgba(217, 119, 6, 0.05)",
            }}
          >
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 12, flexWrap: "wrap", gap: 10 }}>
              <div>
                <h3 style={{ margin: "0 0 4px", fontSize: "1.2rem", color: "#92400e", display: "flex", alignItems: "center", gap: 8 }}>
                  Smart Budget Reallocation Engine
                </h3>
                <p style={{ margin: 0, color: "#b45309", fontSize: "0.86rem" }}>
                  Active Strategy: <strong>{budgetRealloc.strategy_label}</strong> — {budgetRealloc.strategy_description}
                </p>
              </div>

              {/* Strategy Selector Buttons & Apply Action */}
              <div style={{ display: "flex", gap: 6, alignItems: "center", flexWrap: "wrap" }}>
                {budgetRealloc.available_strategies?.map((st: any) => (
                  <button
                    key={st.id}
                    type="button"
                    onClick={() => {
                      setSelectedBudgetStrategy(st.id);
                      handleApplyBudgetReallocation(st.id);
                    }}
                    disabled={reallocatingBudget}
                    style={{
                      padding: "6px 12px",
                      fontSize: "0.78rem",
                      fontWeight: 600,
                      borderRadius: 20,
                      border: "none",
                      cursor: "pointer",
                      background: (selectedBudgetStrategy || budgetRealloc.active_strategy) === st.id ? "#d97706" : "#fef3c7",
                      color: (selectedBudgetStrategy || budgetRealloc.active_strategy) === st.id ? "#ffffff" : "#92400e",
                      boxShadow: (selectedBudgetStrategy || budgetRealloc.active_strategy) === st.id ? "0 2px 4px rgba(217, 119, 6, 0.25)" : "none",
                      transition: "all 0.2s",
                    }}
                  >
                    {st.label}
                  </button>
                ))}

                <button
                  type="button"
                  onClick={() => handleApplyBudgetReallocation(selectedBudgetStrategy || budgetRealloc.active_strategy || "conservative")}
                  disabled={reallocatingBudget}
                  style={{
                    padding: "6px 14px",
                    fontSize: "0.80rem",
                    fontWeight: 700,
                    borderRadius: 20,
                    border: "none",
                    cursor: "pointer",
                    background: "#059669",
                    color: "#ffffff",
                    boxShadow: "0 2px 4px rgba(5, 150, 105, 0.25)",
                    transition: "all 0.2s",
                  }}
                >
                  {reallocatingBudget ? "Reallocating..." : " Apply Smart Allocation"}
                </button>
              </div>
            </div>

            {budgetReallocFeedback && (
              <div
                style={{
                  background: "#f0fdf4",
                  border: "1px solid #bbf7d0",
                  color: "#166534",
                  padding: "8px 14px",
                  borderRadius: 8,
                  fontSize: "0.85rem",
                  marginBottom: 14,
                }}
              >
                ✓ {budgetReallocFeedback}
              </div>
            )}

            {/* Category Before vs After Comparison Table / Cards */}
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(180px, 1fr))", gap: 12, margin: "14px 0" }}>
              {budgetRealloc.categories &&
                Object.entries(budgetRealloc.categories).map(([catKey, catData]: [string, any]) => {
                  const delta = catData.delta_amount;
                  return (
                    <div
                      key={catKey}
                      style={{
                        background: "#ffffff",
                        border: "1px solid #fef3c7",
                        borderRadius: 10,
                        padding: "12px 14px",
                        boxShadow: "0 1px 3px rgba(0,0,0,0.03)",
                      }}
                    >
                      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 4 }}>
                        <span style={{ fontSize: "0.85rem", fontWeight: 700, color: "#1e293b", textTransform: "capitalize" }}>
                          {catKey === "hotel" ? "Hotel" : catKey === "food" ? "Dining" : catKey === "transport" ? "Transport" : catKey === "activities" ? "Activities" : "Reserve"}
                        </span>
                        <span
                          style={{
                            fontSize: "0.72rem",
                            fontWeight: 700,
                            padding: "2px 6px",
                            borderRadius: 10,
                            background: delta > 0 ? "#dcfce7" : delta < 0 ? "#fee2e2" : "#f1f5f9",
                            color: delta > 0 ? "#166534" : delta < 0 ? "#991b1b" : "#475569",
                          }}
                        >
                          {delta > 0 ? `+₹${delta}` : delta < 0 ? `-₹${Math.abs(delta)}` : "Balanced"}
                        </span>
                      </div>

                      <div style={{ fontSize: "0.95rem", fontWeight: 700, color: "#0f172a" }}>
                        ₹{catData.proposed_amount}
                      </div>

                      <div style={{ fontSize: "0.74rem", color: "#64748b", marginTop: 2 }}>
                        Current: ₹{catData.current_amount} ({catData.target_percentage}% target)
                      </div>
                    </div>
                  );
                })}
            </div>

            {/* Actionable Trade-Off Cards */}
            {budgetRealloc.trade_off_suggestions?.length > 0 && (
              <div style={{ marginTop: 12 }}>
                <div style={{ fontSize: "0.85rem", fontWeight: 700, color: "#92400e", marginBottom: 6 }}>
                  High-Impact Budget Trade-Offs:
                </div>
                <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                  {budgetRealloc.trade_off_suggestions.map((to: any, toIdx: number) => (
                    <div
                      key={toIdx}
                      style={{
                        background: "#ffffff",
                        border: "1px solid #fef3c7",
                        borderRadius: 8,
                        padding: "10px 14px",
                        fontSize: "0.82rem",
                        color: "#334155",
                      }}
                    >
                      <strong style={{ color: "#b45309" }}>{to.action}</strong>
                      <div style={{ marginTop: 2, color: "#475569" }}>{to.impact}</div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

      </div>


      <div className="section card">

        <h2 className="section-title">
          Travelers
        </h2>

        {trip.travelers && trip.travelers.length > 0 ? (
          trip.travelers.map(
            (
              traveler: Traveler,
              index: number
            ) => (
              <div key={index}>
                <strong>
                  {traveler.name}
                </strong>

                {" - "}

                {traveler.budget}
              </div>
            )
          )
        ) : (
          <p style={{ color: "#64748b", fontStyle: "italic", margin: 0 }}>
            No travelers specified.
          </p>
        )}

      </div>

      {/* Group Decision & Conflict Resolution Card */}
      {groupDecisions && (
        <div
          id="section-group-decisions"
          style={{
            background: "#f8fafc",
            border: "1px solid #cbd5e1",
            borderRadius: 12,
            padding: "20px 24px",
            margin: "24px 0",
            boxShadow: "0 2px 6px rgba(15, 23, 42, 0.05)",
          }}
        >
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 14, flexWrap: "wrap", gap: 10 }}>
            <div>
              <h3 style={{ margin: "0 0 4px", fontSize: "1.2rem", color: "#0f172a", display: "flex", alignItems: "center", gap: 8 }}>
                Group Decision & Conflict Resolution
              </h3>
              <p style={{ margin: 0, color: "#64748b", fontSize: "0.86rem" }}>
                Multi-traveler consensus balancing, satisfaction meters & collaborative itinerary voting.
              </p>
            </div>

            <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
              <span
                style={{
                  background: groupDecisions.harmony_score >= 75 ? "#dcfce7" : "#fee2e2",
                  color: groupDecisions.harmony_score >= 75 ? "#166534" : "#991b1b",
                  border: `1px solid ${groupDecisions.harmony_score >= 75 ? "#86efac" : "#fca5a5"}`,
                  padding: "4px 12px",
                  borderRadius: 16,
                  fontSize: "0.82rem",
                  fontWeight: 700,
                }}
              >
                {groupDecisions.harmony_score}% Harmony ({groupDecisions.harmony_level})
              </span>

              <button
                type="button"
                disabled={resolvingConflicts}
                onClick={handleResolveConflicts}
                style={{
                  padding: "6px 14px",
                  fontSize: "0.8rem",
                  fontWeight: 600,
                  borderRadius: 8,
                  border: "none",
                  cursor: resolvingConflicts ? "default" : "pointer",
                  background: resolvingConflicts ? "#94a3b8" : "#2563eb",
                  color: "#ffffff",
                  transition: "background 0.2s",
                }}
              >
                {resolvingConflicts ? "Optimizing..." : "Auto-Resolve Conflicts"}
              </button>
            </div>
          </div>

          {groupConflictFeedback && (
            <div
              style={{
                background: "#f0fdf4",
                border: "1px solid #bbf7d0",
                color: "#166534",
                padding: "8px 14px",
                borderRadius: 8,
                fontSize: "0.85rem",
                marginBottom: 14,
              }}
            >
              ✓ {groupConflictFeedback}
            </div>
          )}

          {/* Detected Conflicts */}
          {groupDecisions.detected_conflicts?.length > 0 && (
            <div style={{ marginBottom: 16 }}>
              <h4 style={{ margin: "0 0 8px", fontSize: "0.92rem", color: "#991b1b", display: "flex", alignItems: "center", gap: 6 }}>
                ⚠️ Detected Group Conflicts ({groupDecisions.detected_conflicts.length})
              </h4>
              <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                {groupDecisions.detected_conflicts.map((conf: any, cIdx: number) => (
                  <div
                    key={cIdx}
                    style={{
                      background: "#fef2f2",
                      border: "1px solid #fecaca",
                      borderRadius: 8,
                      padding: "10px 14px",
                      fontSize: "0.82rem",
                      color: "#991b1b",
                    }}
                  >
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 4 }}>
                      <strong>{conf.place_name}</strong>
                      <span
                        style={{
                          fontSize: "0.72rem",
                          padding: "2px 8px",
                          borderRadius: 10,
                          background: conf.conflict_type === "unanimous_skip" ? "#fee2e2" : "#ffedd5",
                          color: conf.conflict_type === "unanimous_skip" ? "#991b1b" : "#c2410c",
                          fontWeight: 700,
                        }}
                      >
                        {conf.conflict_type === "unanimous_skip" ? "Unanimous Skip Requested" : "Split Preference"}
                      </span>
                    </div>
                    <div style={{ color: "#7f1d1d", fontSize: "0.78rem", marginBottom: 4 }}>
                      Favor: {conf.favor_voters?.join(", ") || "None"} | Skip: {conf.skip_voters?.join(", ") || "None"} (Consensus Score: {conf.consensus_score})
                    </div>
                    <div style={{ background: "#ffffff", padding: "6px 10px", borderRadius: 6, border: "1px solid #fca5a5", fontSize: "0.76rem" }}>
                      <strong>Proposed Resolution:</strong> {conf.proposed_resolution}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Applied Conflict Resolutions */}
          {groupDecisions.applied_resolutions?.length > 0 && (
            <div style={{ marginBottom: 16 }}>
              <h4 style={{ margin: "0 0 8px", fontSize: "0.92rem", color: "#166534", display: "flex", alignItems: "center", gap: 6 }}>
                ✓ Applied Conflict Resolutions ({groupDecisions.applied_resolutions.length})
              </h4>
              <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                {groupDecisions.applied_resolutions.map((resItem: any, rIdx: number) => (
                  <div
                    key={rIdx}
                    style={{
                      background: "#f0fdf4",
                      border: "1px solid #bbf7d0",
                      borderRadius: 8,
                      padding: "10px 14px",
                      fontSize: "0.82rem",
                      color: "#166534",
                    }}
                  >
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 4 }}>
                      <strong>{resItem.attraction}</strong>
                      <span style={{ fontSize: "0.72rem", background: "#dcfce7", color: "#14532d", padding: "2px 8px", borderRadius: 10, fontWeight: 700 }}>
                        {resItem.strategy === "skipped_and_substituted" ? "Substituted with Alternative" : "Split Compromise"}
                      </span>
                    </div>
                    <p style={{ margin: 0, fontSize: "0.78rem" }}>{resItem.resolution}</p>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Divergence Zones Banner */}
          {groupDecisions.divergence_zones?.length > 0 && (
            <div style={{ display: "flex", flexDirection: "column", gap: 6, marginBottom: 16 }}>
              {groupDecisions.divergence_zones.map((dz: any, dzIdx: number) => (
                <div
                  key={dzIdx}
                  style={{
                    background: "#fffbeb",
                    border: "1px solid #fde68a",
                    borderRadius: 8,
                    padding: "8px 12px",
                    fontSize: "0.82rem",
                    color: "#92400e",
                    display: "flex",
                    justifyContent: "space-between",
                    alignItems: "center",
                    flexWrap: "wrap",
                    gap: 6,
                  }}
                >
                  <div>
                    <strong>{dz.category}:</strong> {dz.description}
                  </div>
                  <span style={{ fontSize: "0.75rem", color: "#b45309", fontStyle: "italic" }}>
                    Suggestion: {dz.suggestion}
                  </span>
                </div>
              ))}
            </div>
          )}

          {/* Traveler Satisfaction Breakdown */}
          <div style={{ marginBottom: 16 }}>
            <h4 style={{ margin: "0 0 10px", fontSize: "0.95rem", color: "#334155" }}>
              Traveler Preference Fulfillment:
            </h4>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(240px, 1fr))", gap: 12 }}>
              {groupDecisions.traveler_satisfaction?.map((ts: any, tsIdx: number) => (
                <div
                  key={tsIdx}
                  style={{
                    background: "#ffffff",
                    border: "1px solid #e2e8f0",
                    borderRadius: 8,
                    padding: "12px 14px",
                  }}
                >
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 6 }}>
                    <strong style={{ fontSize: "0.9rem", color: "#0f172a" }}>{ts.traveler}</strong>
                    <span style={{ fontSize: "0.8rem", fontWeight: 700, color: ts.score >= 70 ? "#16a34a" : "#d97706" }}>
                      {ts.score}% Sat.
                    </span>
                  </div>

                  {/* Progress bar */}
                  <div style={{ height: 6, width: "100%", background: "#f1f5f9", borderRadius: 3, overflow: "hidden", marginBottom: 8 }}>
                    <div
                      style={{
                        height: "100%",
                        width: `${ts.score}%`,
                        background: ts.score >= 70 ? "#22c55e" : "#f59e0b",
                        borderRadius: 3,
                      }}
                    />
                  </div>

                  <div style={{ fontSize: "0.74rem", color: "#64748b" }}>
                    {ts.satisfied_count} of {ts.total_interests} preferences scheduled
                  </div>

                  {ts.represented_interests?.length > 0 && (
                    <div style={{ display: "flex", flexWrap: "wrap", gap: 4, marginTop: 6 }}>
                      {ts.represented_interests.map((ri: string, rIdx: number) => (
                        <span key={rIdx} style={{ fontSize: "0.68rem", background: "#f0fdf4", color: "#166534", padding: "1px 5px", borderRadius: 4 }}>
                          ✓ {ri}
                        </span>
                      ))}
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>

          {/* Group Voting Section */}
          <div>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 10, flexWrap: "wrap", gap: 8 }}>
              <h4 style={{ margin: 0, fontSize: "0.95rem", color: "#334155" }}>
                Group Voting on Scheduled Attractions:
              </h4>

              <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
                <label style={{ fontSize: "0.78rem", color: "#64748b" }}>Vote as:</label>
                <select
                  value={votingTraveler || trip.travelers?.[0]?.name || ""}
                  onChange={(e) => setVotingTraveler(e.target.value)}
                  style={{
                    padding: "4px 8px",
                    fontSize: "0.8rem",
                    borderRadius: 6,
                    border: "1px solid #cbd5e1",
                    background: "#fff",
                  }}
                >
                  {trip.travelers?.map((tr: any, idx: number) => (
                    <option key={idx} value={tr.name}>
                      {tr.name}
                    </option>
                  ))}
                </select>
              </div>
            </div>

            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(280px, 1fr))", gap: 10 }}>
              {groupDecisions.consensus_places?.slice(0, 8).map((cp: any, cpIdx: number) => {
                const currentVoter = votingTraveler || trip.travelers?.[0]?.name || "";
                const voterCurrentChoice = cp.votes_by_traveler?.[currentVoter];

                return (
                  <div
                    key={cpIdx}
                    style={{
                      background: "#ffffff",
                      border: cp.status.includes("Contentious") ? "1px solid #fecaca" : "1px solid #e2e8f0",
                      borderRadius: 8,
                      padding: "10px 12px",
                      display: "flex",
                      flexDirection: "column",
                      justifyContent: "space-between",
                    }}
                  >
                    <div>
                      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: 6, marginBottom: 4 }}>
                        <strong style={{ fontSize: "0.88rem", color: "#1e293b" }}>{cp.name}</strong>
                        <span
                          style={{
                            fontSize: "0.68rem",
                            padding: "2px 6px",
                            borderRadius: 10,
                            fontWeight: 600,
                            background: cp.status.includes("Contentious") ? "#fee2e2" : "#f1f5f9",
                            color: cp.status.includes("Contentious") ? "#991b1b" : "#475569",
                          }}
                        >
                          {cp.status}
                        </span>
                      </div>
                      <div style={{ fontSize: "0.74rem", color: "#64748b", marginBottom: 6 }}>
                        Favor: {cp.up_votes} | Neutral: {cp.neutral_votes} | Skip: {cp.down_votes}
                      </div>
                    </div>

                    <div style={{ display: "flex", gap: 6, marginTop: 4 }}>
                      <button
                        type="button"
                        disabled={votingLoading}
                        onClick={() => handleCastVote(cp.name, "up")}
                        style={{
                          flex: 1,
                          padding: "4px 8px",
                          fontSize: "0.75rem",
                          borderRadius: 6,
                          border: "1px solid #bbf7d0",
                          background: voterCurrentChoice === "up" ? "#22c55e" : "#f0fdf4",
                          color: voterCurrentChoice === "up" ? "#fff" : "#166534",
                          cursor: "pointer",
                        }}
                      >
                        Favor
                      </button>
                      <button
                        type="button"
                        disabled={votingLoading}
                        onClick={() => handleCastVote(cp.name, "neutral")}
                        style={{
                          flex: 1,
                          padding: "4px 8px",
                          fontSize: "0.75rem",
                          borderRadius: 6,
                          border: "1px solid #e2e8f0",
                          background: voterCurrentChoice === "neutral" ? "#64748b" : "#f8fafc",
                          color: voterCurrentChoice === "neutral" ? "#fff" : "#475569",
                          cursor: "pointer",
                        }}
                      >
                        Neutral
                      </button>
                      <button
                        type="button"
                        disabled={votingLoading}
                        onClick={() => handleCastVote(cp.name, "down")}
                        style={{
                          flex: 1,
                          padding: "4px 8px",
                          fontSize: "0.75rem",
                          borderRadius: 6,
                          border: "1px solid #fecaca",
                          background: voterCurrentChoice === "down" ? "#ef4444" : "#fef2f2",
                          color: voterCurrentChoice === "down" ? "#fff" : "#991b1b",
                          cursor: "pointer",
                        }}
                      >
                        Skip
                      </button>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      )}


      <div id="section-weather" className="section">

        <h2 className="section-title">
          Weather Forecast & Itinerary Alerts
        </h2>

        <WeatherAlertsBanner
          weatherData={weatherAlertsData}
          loading={weatherLoading}
          error={weatherError}
        />

        {!weatherAlertsData && !weatherLoading && normalizedWeather.length > 0 && (
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(200px, 1fr))", gap: 12, marginTop: 12 }}>
            {normalizedWeather.map((weather, index) => (
              <WeatherCard key={index} weather={weather} />
            ))}
          </div>
        )}


        {trip.transport && (
          <div className="card">

            <h3>Transportation</h3>

            <p>
              <strong>
                {trip.transport.label}
              </strong>
            </p>

            <p>
              {trip.transport.description}
            </p>

            <div className="transport-summary">

              <div>
                <strong>
                  {trip.transport.distance_km} km
                </strong>

                <span>
                  Total Distance
                </span>
              </div>

              <div>
                <strong>
                  {trip.transport.duration_hours} hrs
                </strong>

                <span>
                  Total Duration
                </span>
              </div>

            </div>


            {Array.isArray(trip.transport.legs) && trip.transport.legs.length > 0 && (
              <div className="transport-legs">

                {trip.transport.legs.map(
                  (leg, index) => (

                    <div
                      key={index}
                      className="transport-leg"
                    >

                      <div>

                        <strong>
                          {leg.type}
                        </strong>

                        <p>
                          {leg.from} → {leg.to}
                        </p>

                      </div>


                      <div>

                        <span>
                          {leg.distance_km} km
                        </span>

                        <span>
                          {leg.duration_hours} hrs
                        </span>

                      </div>

                    </div>

                  )
                )}

              </div>
            )}

          </div>
        )}

        {/* Transport Recommendation Engine & Trade-off Matrix */}
        {transportRecs && (
          <div
            id="section-transport"
            style={{
              background: "#f0fdf4",
              border: "1px solid #bbf7d0",
              borderRadius: 12,
              padding: "20px 24px",
              marginTop: 16,
              boxShadow: "0 2px 6px rgba(22, 101, 52, 0.05)",
            }}
          >
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 12, flexWrap: "wrap", gap: 10 }}>
              <div>
                <h3 style={{ margin: "0 0 4px", fontSize: "1.2rem", color: "#166534", display: "flex", alignItems: "center", gap: 8 }}>
                  Transport Recommendation Engine
                </h3>
                <p style={{ margin: 0, color: "#15803d", fontSize: "0.86rem" }}>
                  Multi-modal comparison across Party Size ({transportRecs.party_size || 1}), Distance ({transportRecs.distance_km} km), Cost, Time & Carbon emissions.
                </p>
              </div>

              <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
                <span
                  style={{
                    background: transportRecs.is_using_recommended ? "#dcfce7" : "#fef3c7",
                    color: transportRecs.is_using_recommended ? "#166534" : "#92400e",
                    border: `1px solid ${transportRecs.is_using_recommended ? "#86efac" : "#fcd34d"}`,
                    padding: "4px 12px",
                    borderRadius: 16,
                    fontSize: "0.8rem",
                    fontWeight: 700,
                  }}
                >
                  {transportRecs.is_using_recommended
                    ? `✓ Active: Recommended (${transportRecs.recommended_mode?.toUpperCase()})`
                    : `Active: ${transportRecs.current_mode?.toUpperCase()} (Recommended: ${transportRecs.recommended_mode?.toUpperCase()})`}
                </span>
              </div>
            </div>

            {/* AI Recommendation Summary Banner */}
            <div
              style={{
                background: "#ffffff",
                border: "1px solid #86efac",
                borderRadius: 8,
                padding: "12px 16px",
                marginBottom: 16,
                fontSize: "0.88rem",
                color: "#1e293b",
                lineHeight: 1.5,
              }}
            >
              <strong>Recommendation Rationale:</strong> {transportRecs.recommendation_summary}
            </div>

            {transportStatusMessage && (
              <div
                style={{
                  background: "#dcfce7",
                  border: "1px solid #86efac",
                  color: "#166534",
                  padding: "8px 14px",
                  borderRadius: 8,
                  fontSize: "0.85rem",
                  marginBottom: 14,
                }}
              >
                ✓ {transportStatusMessage}
              </div>
            )}

            {/* Comparison Grid across Car, Train, Flight, Bus */}
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(260px, 1fr))", gap: 14 }}>
              {transportRecs.options &&
                Object.entries(transportRecs.options).map(([modeKey, opt]: [string, any]) => {
                  const currentMode = ((trip as any).travel_mode || (trip.transport as any)?.travel_mode || trip.transport?.mode || "");
                  const isSelected = currentMode.toLowerCase() === modeKey.toLowerCase();
                  const isRec = transportRecs.recommended_mode?.toLowerCase() === modeKey.toLowerCase();

                  return (
                    <div
                      key={modeKey}
                      style={{
                        background: isSelected ? "#ffffff" : "#f8fafc",
                        border: isSelected ? "2px solid #16a34a" : isRec ? "1px solid #86efac" : "1px solid #e2e8f0",
                        borderRadius: 10,
                        padding: "16px",
                        display: "flex",
                        flexDirection: "column",
                        justifyContent: "space-between",
                        boxShadow: isSelected ? "0 4px 12px rgba(22, 163, 74, 0.12)" : "none",
                        position: "relative",
                      }}
                    >
                      <div>
                        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 6 }}>
                          <span style={{ fontSize: "1.05rem", fontWeight: 700, color: "#1e293b", textTransform: "capitalize" }}>
                            {modeKey === "car" ? "Car / Drive" : modeKey === "train" ? "Train / Rail" : modeKey === "flight" ? "Flight" : "Bus"}
                          </span>
                          <span
                            style={{
                              fontSize: "0.78rem",
                              fontWeight: 700,
                              background: opt.score >= 80 ? "#dcfce7" : "#e0e7ff",
                              color: opt.score >= 80 ? "#166534" : "#3730a3",
                              padding: "2px 8px",
                              borderRadius: 12,
                            }}
                          >
                            Score: {opt.score}/100
                          </span>
                        </div>

                        {/* Badges */}
                        <div style={{ display: "flex", flexWrap: "wrap", gap: 4, marginBottom: 10 }}>
                          {opt.badges?.map((b: string, bIdx: number) => (
                            <span
                              key={bIdx}
                              style={{
                                fontSize: "0.7rem",
                                fontWeight: 600,
                                background: b.includes("Recommended") ? "#fef08a" : b.includes("Fastest") ? "#fed7aa" : b.includes("Eco") ? "#bbf7d0" : "#f1f5f9",
                                color: "#1e293b",
                                padding: "1px 6px",
                                borderRadius: 4,
                              }}
                            >
                              {b}
                            </span>
                          ))}
                        </div>

                        {/* Metrics Breakdown */}
                        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8, margin: "10px 0", fontSize: "0.8rem" }}>
                          <div style={{ background: "#f1f5f9", padding: "6px 8px", borderRadius: 6 }}>
                            <div style={{ color: "#64748b", fontSize: "0.72rem" }}>Est. Cost (Total)</div>
                            <strong style={{ color: "#0f172a" }}>₹{opt.total_cost_inr}</strong>
                            <div style={{ color: "#94a3b8", fontSize: "0.68rem" }}>₹{opt.per_person_cost_inr}/person</div>
                          </div>
                          <div style={{ background: "#f1f5f9", padding: "6px 8px", borderRadius: 6 }}>
                            <div style={{ color: "#64748b", fontSize: "0.72rem" }}>Transit Time</div>
                            <strong style={{ color: "#0f172a" }}>{opt.duration_hours} hrs</strong>
                          </div>
                          <div style={{ background: "#f1f5f9", padding: "6px 8px", borderRadius: 6 }}>
                            <div style={{ color: "#64748b", fontSize: "0.72rem" }}>CO2 Emissions</div>
                            <strong style={{ color: "#0f172a" }}>{opt.carbon_kg} kg</strong>
                          </div>
                          <div style={{ background: "#f1f5f9", padding: "6px 8px", borderRadius: 6 }}>
                            <div style={{ color: "#64748b", fontSize: "0.72rem" }}>Comfort / Ease</div>
                            <strong style={{ color: "#0f172a" }}>{opt.comfort_score}/10</strong>
                          </div>
                        </div>

                        <p style={{ margin: "6px 0 12px", fontSize: "0.78rem", color: "#475569", lineHeight: 1.4 }}>
                          {opt.suitability_reason}
                        </p>
                      </div>

                      <button
                        type="button"
                        disabled={isSelected || switchingTransport || !opt.viable}
                        onClick={() => handleSwitchTransport(modeKey)}
                        style={{
                          width: "100%",
                          padding: "8px 12px",
                          fontSize: "0.82rem",
                          fontWeight: 700,
                          borderRadius: 6,
                          border: "none",
                          cursor: isSelected || !opt.viable ? "default" : "pointer",
                          background: isSelected ? "#16a34a" : opt.viable ? "#0f172a" : "#94a3b8",
                          color: "#ffffff",
                          transition: "background 0.2s",
                        }}
                      >
                        {isSelected ? "✓ Currently Active" : !opt.viable ? "Not Viable" : switchingTransport ? "Switching..." : `Switch to ${modeKey.toUpperCase()}`}
                      </button>
                    </div>
                  );
                })}
            </div>
          </div>
        )}

      </div>

        <div className="section card">
  <h2>Trip Notes</h2>

  <div style={{ display: "flex", gap: "10px" }}>
    <input
      type="text"
      value={newNote}
      onChange={(e) => setNewNote(e.target.value)}
      placeholder="Add a note..."
      style={{
        flex: 1,
        padding: "10px",
      }}
    />

    <button
      onClick={async () => {
        if (!newNote.trim()) return;

        try {
          const updatedNotes = await addTripNote(
            tripId,
            newNote
          );

          setNotes(updatedNotes);
          setNewNote("");
        } catch (error) {
          console.error(
            "Failed to add note:",
            error
          );
        }
      }}
    >
      Add Note
    </button>
  </div>

  {notes.length === 0 ? (
    <p>No notes yet.</p>
  ) : (
    <ul>
      {notes.map((note, index) => (
        <li key={index}>
          <span>{note}</span>

          <button
            onClick={async () => {
              try {
                await deleteTripNote(
                  tripId,
                  index
                );

                const updatedNotes =
                  await getTripNotes(tripId);

                setNotes(updatedNotes);
              } catch (error) {
                console.error(
                  "Failed to delete note:",
                  error
                );
              }
            }}
            style={{
              marginLeft: "10px",
            }}
          >
            Delete
          </button>
        </li>
      ))}
    </ul>
  )}
</div>
      <div className="section card">

        <h2>Edit Your Trip</h2>

        <p>
          Tell TravelSync AI what you want to change.
        </p>

        <textarea
          value={editPrompt}
          onChange={(e) =>
            setEditPrompt(e.target.value)
          }
          placeholder='Try: "Add Charminar"'
          rows={3}
          style={{
            width: "100%",
            padding: "10px",
            marginTop: "10px",
            marginBottom: "10px",
            resize: "vertical",
          }}
        />

        <button
          className="regenerate-button"
          onClick={handleTripEdit}
          disabled={
            updating ||
            !editPrompt.trim()
          }
        >
          {updating
            ? "Updating..."
            : "Apply Changes"}
        </button>

        <p style={{ marginTop: "10px" }}>
          Try: "Add Charminar", "Remove Charminar",
          "Regenerate Day 2", or
          "Keep budget under ₹30000"
        </p>

      </div>


      <div id="section-itinerary" className="section">

        <h2 className="section-title">
          Daily Plan
        </h2>

        {attractionActionMessage && (
          <div
            style={{
              padding: "10px 16px",
              borderRadius: 8,
              marginBottom: 16,
              fontSize: "0.88rem",
              fontWeight: 500,
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
              background: attractionActionMessage.type === "success" ? "#f0fdf4" : "#fef2f2",
              color: attractionActionMessage.type === "success" ? "#166534" : "#991b1b",
              border: `1px solid ${attractionActionMessage.type === "success" ? "#bbf7d0" : "#fecaca"}`,
            }}
          >
            <span>{attractionActionMessage.type === "success" ? "✓" : "⚠️"} {attractionActionMessage.text}</span>
            <button
              type="button"
              onClick={() => setAttractionActionMessage(null)}
              style={{
                background: "transparent",
                border: "none",
                fontSize: "1rem",
                cursor: "pointer",
                color: "inherit",
                marginLeft: 12,
              }}
            >
              ✕
            </button>
          </div>
        )}

        {trip.day_schedule &&
          Object.entries(
            trip.day_schedule
          ).map(
            ([day, places]) => (

              <DayCard
                key={day}
                day={day}
                places={places}
                TravelMode={trip.transport?.mode || trip.travel_mode || "car"}
                mealsAndBreaks={(trip as any)?.meals_and_breaks?.[day]}
                onSelect={
                  setSelectedPlace
                }
                onRegenerate={
                  handleRegenerateDay
                }
                onReplanDay={
                  handleOpenReplan
                }
                onRemoveAttraction={
                  handleOpenRemoveAttraction
                }
                onReplaceAttraction={
                  handleOpenReplaceAttraction
                }
                onShowPlaceInfo={
                  handleShowPlaceInfo
                }
              />



            )
          )}

        {/* Recommended Accommodations Section */}
        {Array.isArray(trip.hotels) && trip.hotels.length > 0 && (
          <div style={{ marginTop: 24, borderTop: "1px solid #e2e8f0", paddingTop: 20 }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 14 }}>
              <div>
                <h3 style={{ margin: 0, fontSize: "1.15rem", color: "#1e293b", display: "flex", alignItems: "center", gap: 8 }}>
                  🏨 Recommended Accommodations ({trip.hotels.length})
                </h3>
                <p style={{ margin: "2px 0 0", fontSize: "0.84rem", color: "#64748b" }}>
                  Selected hotel options near your destination itinerary.
                </p>
              </div>
            </div>

            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(260px, 1fr))", gap: 12 }}>
              {trip.hotels.map((hotel: any, hIdx: number) => (
                <div
                  key={hIdx}
                  style={{
                    background: "#ffffff",
                    borderRadius: 10,
                    border: "1px solid #e2e8f0",
                    padding: "14px 16px",
                    display: "flex",
                    flexDirection: "column",
                    justifyContent: "space-between",
                    boxShadow: "0 1px 3px rgba(0,0,0,0.04)",
                  }}
                >
                  <div>
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: 6, marginBottom: 4 }}>
                      <strong style={{ fontSize: "0.95rem", color: "#0f172a" }}>{hotel.name}</strong>
                      <button
                        type="button"
                        className="hotel-info-btn"
                        aria-label={`View details for ${hotel.name}`}
                        title={`View details for ${hotel.name}`}
                        style={{
                          background: "#e0e7ff",
                          border: "1px solid #c7d2fe",
                          color: "#4338ca",
                          borderRadius: "50%",
                          width: 22,
                          height: 22,
                          display: "inline-flex",
                          alignItems: "center",
                          justifyContent: "center",
                          fontSize: "0.78rem",
                          fontWeight: 700,
                          cursor: "pointer",
                          padding: 0,
                          lineHeight: 1,
                          flexShrink: 0,
                        }}
                        onClick={() => handleShowPlaceInfo({
                          name: hotel.name,
                          place_type: "hotel",
                          category: "Hotel Accommodation",
                          lat: hotel.lat,
                          lon: hotel.lon,
                          distance_km: hotel.distance_km,
                        })}
                      >
                        ⓘ
                      </button>
                    </div>
                    <p style={{ margin: "2px 0 8px", fontSize: "0.82rem", color: "#64748b" }}>
                      Hotel • {hotel.distance_km != null ? `${hotel.distance_km} km from arrival center` : "Near destination"}
                    </p>
                  </div>

                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", borderTop: "1px dashed #e2e8f0", paddingTop: 8, marginTop: 4 }}>
                    <span style={{ fontSize: "0.78rem", color: "#475569", fontWeight: 500 }}>
                      Lodging Option
                    </span>
                    <button
                      type="button"
                      aria-label={`View details for ${hotel.name}`}
                      style={{
                        fontSize: "0.76rem",
                        padding: "4px 10px",
                        borderRadius: 6,
                        border: "1px solid #bfdbfe",
                        background: "#eff6ff",
                        color: "#1d4ed8",
                        cursor: "pointer",
                        fontWeight: 600,
                        display: "inline-flex",
                        alignItems: "center",
                        gap: 4,
                      }}
                      onClick={() => handleShowPlaceInfo({
                        name: hotel.name,
                        place_type: "hotel",
                        category: "Hotel Accommodation",
                        lat: hotel.lat,
                        lon: hotel.lon,
                        distance_km: hotel.distance_km,
                      })}
                    >
                      <span>ⓘ</span> Hotel Details
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

      </div>


      <div className="section">

        <h2 className="section-title">
          Map
        </h2>

        {typeof trip.destination_location?.lat === "number" &&
        !isNaN(trip.destination_location.lat) &&
        typeof trip.destination_location?.lon === "number" &&
        !isNaN(trip.destination_location.lon) ? (
          <MapView
            lat={trip.destination_location.lat}
            lon={trip.destination_location.lon}
            places={trip.places || []}
            hotels={trip.hotels || []}
            selectedPlace={selectedPlace}
            routeCoordinates={trip.route_coordinates || []}
          />
        ) : (
          <div className="card" style={{ padding: "20px", textAlign: "center", color: "#64748b" }}>
            <p style={{ margin: 0 }}>Map coordinates are not available for this trip location.</p>
          </div>
        )}

      </div>


      {data.itinerary?.days && (
        <div className="section">

          <h2 className="section-title">
            AI Itinerary
          </h2>

          {data.itinerary.days.map(
            (day) => (

              <div
                key={day.day}
                className="card"
              >

                <h3>
                  Day {day.day}:{" "}
                  {day.title}
                </h3>

                <h4>
                  Activities
                </h4>

                <ul>
                  {day.activities.map(
                    (
                      activity,
                      index
                    ) => (
                      <li key={index}>
                        {activity}
                      </li>
                    )
                  )}
                </ul>


                <h4>
                  Food
                </h4>

                <ul>
                  {day.food.map(
                    (food, index) => (
                      <li key={index}>
                        {food}
                      </li>
                    )
                  )}
                </ul>


                <p>
                  <strong>
                    Budget:
                  </strong>{" "}
                  {day.budget}
                </p>

              </div>

            )
          )}

        </div>
      )}


      <div className="section">

        <AddExpenseModal
          travelers={(trip.travelers || []).map(
            (traveler) =>
              traveler.name
          )}
          onAdd={handleAddExpense}
        />

      </div>


      {expenseData && (
        <div className="section">

          <BudgetAlerts
            alerts={expenseData.alerts}
          />

          <h2 className="section-title">
            Trip Expenses
          </h2>

          <ExpenseCard
            total={
              expenseData.expenses.reduce(
                (sum, expense) =>
                  sum + expense.amount,
                0
              )
            }
          />

          <ExpenseTable
            expenses={
              expenseData.expenses
            }
          />

          <SettlementCard
            settlements={
              expenseData.settlements
            }
          />

        </div>
      )}

      <div className="section card">
  <h2>Rate This Trip</h2>

 <div>
  {[1, 2, 3, 4, 5].map((star) => (
    <button
      key={star}
      type="button"
      onClick={() => {
        setTripRating(star);
        setRatingSaved(false);
      }}
      style={{
        fontSize: "32px",
        padding: "4px 8px",
        border: "none",
        background: "transparent",
        cursor: "pointer",
        color:
          tripRating !== null && star <= tripRating
            ? "gold"
            : "gray",
      }}
    >
      {tripRating !== null && star <= tripRating
        ? "★"
        : "☆"}
    </button>
  ))}
</div>

  <textarea
    value={ratingFeedback}
    onChange={(e) => {
      setRatingFeedback(e.target.value);
      setRatingSaved(false);
    }}
    placeholder="Optional feedback..."
    rows={3}
    style={{
      width: "100%",
      marginTop: "10px",
      padding: "10px",
    }}
  />

  <button
    type="button"
    disabled={tripRating === null}
    onClick={async () => {
      if (tripRating === null) return;

      try {
        await rateTrip(
          tripId,
          tripRating,
          ratingFeedback
        );

        setRatingSaved(true);
      } catch (error) {
        console.error(
          "Failed to save rating:",
          error
        );
      }
    }}
    style={{
      marginTop: "10px",
    }}
  >
    Save Rating
  </button>

  {ratingSaved && (
    <p>Rating saved successfully.</p>
  )}
</div>
      <div
        style={{
          display: "flex",
          justifyContent: "flex-end",
          gap: 12,
          marginTop: 30,
        }}
      >

        <button
          className="download-button"
          onClick={handleDuplicateTrip}
          disabled={duplicating}
          style={{
            background: "#0284c7",
          }}
        >
          {duplicating ? "Duplicating..." : "Duplicate Trip"}
        </button>

        <button
          className="download-button"
          onClick={() => {
            if (dashboard) {
              setTemplateName(`${dashboard.days || 1}-Day ${dashboard.destination || "Trip"} Template`);
            }
            setShowTemplateModal(true);
          }}
          style={{
            background: "#7c3aed",
          }}
        >
          Save as Template
        </button>

        <button
          className="download-button"
          onClick={() => {
            if (tripId) {
              exportTrip(tripId);
            }
          }}
          style={{
            background: "#4f46e5",
          }}
        >
          Export Trip
        </button>

        <button
          className="download-button export-calendar-btn"
          aria-label="Export itinerary to calendar (.ics)"
          onClick={() => {
            if (tripId) {
              exportTripCalendar(tripId);
            }
          }}
          style={{
            background: "#059669",
          }}
          title="Download .ics calendar file for Google Calendar, Apple Calendar, and Outlook"
        >
          📅 Export to Calendar
        </button>

        <button
          className="download-button"
          onClick={() => {
            if (tripId) {
              downloadTripPdf(tripId);
            }
          }}
        >
          Download PDF
        </button>

      </div>

      {/* SAVE TRIP AS TEMPLATE MODAL */}
      {showTemplateModal && (
        <div
          style={{
            position: "fixed",
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            backgroundColor: "rgba(0,0,0,0.5)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            zIndex: 1000,
            padding: 20,
          }}
        >
          <div
            style={{
              background: "#fff",
              borderRadius: 12,
              padding: 24,
              maxWidth: 480,
              width: "100%",
              boxShadow: "0 20px 25px -5px rgba(0,0,0,0.2)",
            }}
          >
            <h3 style={{ margin: "0 0 8px", fontSize: "1.25rem", color: "#1e293b" }}>
              Save Trip as Template
            </h3>
            <p style={{ margin: "0 0 16px", color: "#64748b", fontSize: "0.88rem" }}>
              Make this itinerary a reusable blueprint for future trip planning.
            </p>

            <div style={{ marginBottom: 14 }}>
              <label style={{ display: "block", fontSize: "0.84rem", fontWeight: 600, color: "#334155", marginBottom: 4 }}>
                Template Name
              </label>
              <input
                type="text"
                value={templateName}
                onChange={(e) => setTemplateName(e.target.value)}
                placeholder="e.g. 3-Day Goa Leisure & Beach Escape"
                style={{
                  width: "100%",
                  padding: "8px 12px",
                  borderRadius: 6,
                  border: "1px solid #cbd5e1",
                  boxSizing: "border-box",
                  fontSize: "0.9rem",
                }}
              />
            </div>

            <div style={{ marginBottom: 14 }}>
              <label style={{ display: "block", fontSize: "0.84rem", fontWeight: 600, color: "#334155", marginBottom: 4 }}>
                Category
              </label>
              <select
                value={templateCategory}
                onChange={(e) => setTemplateCategory(e.target.value)}
                style={{
                  width: "100%",
                  padding: "8px 12px",
                  borderRadius: 6,
                  border: "1px solid #cbd5e1",
                  background: "#fff",
                  boxSizing: "border-box",
                  fontSize: "0.9rem",
                }}
              >
                <option value="General">General</option>
                <option value="Weekend Getaway">Weekend Getaway</option>
                <option value="Heritage & Culture">Heritage & Culture</option>
                <option value="Beach & Leisure">Beach & Leisure</option>
                <option value="Adventure">Adventure</option>
                <option value="Family Friendly">Family Friendly</option>
              </select>
            </div>

            <div style={{ marginBottom: 20 }}>
              <label style={{ display: "block", fontSize: "0.84rem", fontWeight: 600, color: "#334155", marginBottom: 4 }}>
                Description (Optional)
              </label>
              <textarea
                value={templateDesc}
                onChange={(e) => setTemplateDesc(e.target.value)}
                placeholder="Describe what makes this template great..."
                rows={3}
                style={{
                  width: "100%",
                  padding: "8px 12px",
                  borderRadius: 6,
                  border: "1px solid #cbd5e1",
                  boxSizing: "border-box",
                  fontSize: "0.9rem",
                  fontFamily: "inherit",
                }}
              />
            </div>

            <div style={{ display: "flex", justifyContent: "flex-end", gap: 10 }}>
              <button
                onClick={() => setShowTemplateModal(false)}
                disabled={savingTemplate}
                style={{
                  padding: "8px 16px",
                  borderRadius: 6,
                  border: "1px solid #cbd5e1",
                  background: "#fff",
                  cursor: "pointer",
                  fontWeight: 600,
                  fontSize: "0.88rem",
                  color: "#475569",
                }}
              >
                Cancel
              </button>
              <button
                onClick={handleSaveAsTemplate}
                disabled={savingTemplate}
                style={{
                  padding: "8px 18px",
                  borderRadius: 6,
                  border: "none",
                  background: "#7c3aed",
                  color: "#fff",
                  cursor: "pointer",
                  fontWeight: 600,
                  fontSize: "0.88rem",
                }}
              >
                {savingTemplate ? "Saving..." : "Save Template"}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Real-Time Day Replanning Modal */}
      {showReplanModal && (
        <div
          style={{
            position: "fixed",
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            background: "rgba(15, 23, 42, 0.65)",
            backdropFilter: "blur(4px)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            zIndex: 1000,
            padding: 20,
          }}
        >
          <div
            style={{
              background: "#ffffff",
              borderRadius: 14,
              padding: "24px 28px",
              maxWidth: 520,
              width: "100%",
              boxShadow: "0 20px 25px -5px rgba(0, 0, 0, 0.2)",
              border: "1px solid #e2e8f0",
            }}
          >
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 14 }}>
              <h3 style={{ margin: 0, fontSize: "1.25rem", color: "#1e1b4b", display: "flex", alignItems: "center", gap: 8 }}>
                Replan Day {replanTargetDay} (Live)
              </h3>
              <button
                onClick={() => setShowReplanModal(false)}
                style={{ background: "none", border: "none", fontSize: "1.2rem", cursor: "pointer", color: "#64748b" }}
              >
                ✕
              </button>
            </div>

            <p style={{ margin: "0 0 16px", color: "#64748b", fontSize: "0.88rem" }}>
              Check completed attractions and specify remaining time. TravelSync AI will replan only the unvisited stops from your current location.
            </p>

            {/* Completed attractions checklist */}
            <div style={{ marginBottom: 18 }}>
              <label style={{ display: "block", fontSize: "0.85rem", fontWeight: 700, color: "#334155", marginBottom: 8 }}>
                Check attractions you have ALREADY visited:
              </label>
              <div style={{ maxHeight: 150, overflowY: "auto", border: "1px solid #e2e8f0", borderRadius: 8, padding: 8, background: "#f8fafc" }}>
                {((data?.trip as any)?.day_schedule?.[String(replanTargetDay)] || []).map((p: any, idx: number) => {
                  const isChecked = replanCompletedAttractions.includes(p.name);
                  return (
                    <label key={idx} style={{ display: "flex", alignItems: "center", gap: 8, padding: "6px 8px", cursor: "pointer", fontSize: "0.85rem" }}>
                      <input
                        type="checkbox"
                        checked={isChecked}
                        onChange={(e) => {
                          if (e.target.checked) {
                            setReplanCompletedAttractions([...replanCompletedAttractions, p.name]);
                          } else {
                            setReplanCompletedAttractions(replanCompletedAttractions.filter(n => n !== p.name));
                          }
                        }}
                      />
                      <span style={{ textDecoration: isChecked ? "line-through" : "none", color: isChecked ? "#64748b" : "#0f172a", fontWeight: isChecked ? 400 : 600 }}>
                        {p.name} ({p.time_window || "Scheduled"})
                      </span>
                    </label>
                  );
                })}
              </div>
            </div>

            {/* Remaining Hours */}
            <div style={{ marginBottom: 16 }}>
              <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 4 }}>
                <label style={{ fontSize: "0.84rem", fontWeight: 600, color: "#334155" }}>
                  Hours Remaining Today:
                </label>
                <span style={{ fontSize: "0.84rem", fontWeight: 700, color: "#4f46e5" }}>
                  {replanRemainingHours} hours
                </span>
              </div>
              <input
                type="range"
                min="1"
                max="8"
                step="0.5"
                value={replanRemainingHours}
                onChange={(e) => setReplanRemainingHours(parseFloat(e.target.value))}
                style={{ width: "100%" }}
              />
            </div>

            {/* Current Location Name */}
            <div style={{ marginBottom: 20 }}>
              <label style={{ display: "block", fontSize: "0.84rem", fontWeight: 600, color: "#334155", marginBottom: 4 }}>
                Current Location (Optional)
              </label>
              <input
                type="text"
                value={replanCurrentLocName}
                onChange={(e) => setReplanCurrentLocName(e.target.value)}
                placeholder="e.g., Near Fort Aguada / Hotel Lobby"
                style={{
                  width: "100%",
                  padding: "8px 12px",
                  borderRadius: 6,
                  border: "1px solid #cbd5e1",
                  boxSizing: "border-box",
                  fontSize: "0.9rem",
                }}
              />
            </div>

            <div style={{ display: "flex", justifyContent: "flex-end", gap: 10 }}>
              <button
                onClick={() => setShowReplanModal(false)}
                disabled={replanLoading}
                style={{
                  padding: "8px 16px",
                  borderRadius: 6,
                  border: "1px solid #cbd5e1",
                  background: "#fff",
                  cursor: "pointer",
                  fontWeight: 600,
                  fontSize: "0.88rem",
                  color: "#475569",
                }}
              >
                Cancel
              </button>
              <button
                onClick={handleExecuteReplan}
                disabled={replanLoading}
                style={{
                  padding: "8px 18px",
                  borderRadius: 6,
                  border: "none",
                  background: "#4f46e5",
                  color: "#fff",
                  cursor: "pointer",
                  fontWeight: 600,
                  fontSize: "0.88rem",
                  boxShadow: "0 2px 4px rgba(79, 70, 229, 0.3)",
                }}
              >
                {replanLoading ? "Replanning..." : "Replan Remaining Day"}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* STEP 59: AI Assistant Floating Copilot Drawer */}
      {!chatOpen && (
        <button
          type="button"
          onClick={() => setChatOpen(true)}
          style={{
            position: "fixed",
            bottom: 24,
            right: 24,
            padding: "12px 20px",
            borderRadius: 30,
            background: "linear-gradient(135deg, #4f46e5 0%, #7c3aed 100%)",
            color: "#ffffff",
            border: "none",
            fontWeight: 700,
            fontSize: "0.92rem",
            cursor: "pointer",
            boxShadow: "0 8px 20px rgba(124, 58, 237, 0.35)",
            zIndex: 999,
            display: "flex",
            alignItems: "center",
            gap: 8,
          }}
        >
          AI Travel Assistant
        </button>
      )}

      {chatOpen && (
        <div
          style={{
            position: "fixed",
            bottom: 24,
            right: 24,
            width: 380,
            maxHeight: 560,
            height: "80vh",
            background: "#ffffff",
            borderRadius: 16,
            border: "1px solid #e2e8f0",
            boxShadow: "0 20px 25px -5px rgba(0, 0, 0, 0.15), 0 8px 10px -6px rgba(0, 0, 0, 0.1)",
            zIndex: 1000,
            display: "flex",
            flexDirection: "column",
            overflow: "hidden",
          }}
        >
          {/* Assistant Header */}
          <div
            style={{
              padding: "14px 18px",
              background: "linear-gradient(135deg, #4f46e5 0%, #7c3aed 100%)",
              color: "#ffffff",
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
            }}
          >
            <div>
              <div style={{ fontWeight: 700, fontSize: "1rem", display: "flex", alignItems: "center", gap: 6 }}>
                TravelSync AI Copilot
              </div>
              <div style={{ fontSize: "0.74rem", opacity: 0.9, marginTop: 2 }}>
                Trip Expert for {(trip as any)?.destination || "your trip"}
              </div>
            </div>

            <button
              type="button"
              onClick={() => setChatOpen(false)}
              style={{
                background: "rgba(255, 255, 255, 0.2)",
                border: "none",
                borderRadius: "50%",
                width: 28,
                height: 28,
                color: "#ffffff",
                cursor: "pointer",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                fontWeight: 700,
              }}
            >
              ✕
            </button>
          </div>

          {/* Message Thread */}
          <div
            style={{
              flex: 1,
              padding: "14px 16px",
              overflowY: "auto",
              display: "flex",
              flexDirection: "column",
              gap: 12,
              background: "#f8fafc",
            }}
          >
            {chatMessages.map((msg, idx) => (
              <div
                key={idx}
                style={{
                  alignSelf: msg.role === "user" ? "flex-end" : "flex-start",
                  maxWidth: "84%",
                  padding: "10px 14px",
                  borderRadius: msg.role === "user" ? "14px 14px 2px 14px" : "14px 14px 14px 2px",
                  background: msg.role === "user" ? "#4f46e5" : "#ffffff",
                  color: msg.role === "user" ? "#ffffff" : "#1e293b",
                  border: msg.role === "user" ? "none" : "1px solid #e2e8f0",
                  fontSize: "0.84rem",
                  lineHeight: 1.45,
                  boxShadow: "0 1px 3px rgba(0,0,0,0.05)",
                  whiteSpace: "pre-line",
                }}
              >
                {msg.text}
              </div>
            ))}

            {chatLoading && (
              <div
                style={{
                  alignSelf: "flex-start",
                  padding: "8px 14px",
                  borderRadius: "14px 14px 14px 2px",
                  background: "#ffffff",
                  border: "1px solid #e2e8f0",
                  fontSize: "0.8rem",
                  color: "#64748b",
                  fontStyle: "italic",
                }}
              >
                Thinking...
              </div>
            )}
          </div>

          {/* Suggestion Chips */}
          <div
            style={{
              padding: "8px 12px",
              background: "#ffffff",
              borderTop: "1px solid #f1f5f9",
              display: "flex",
              flexWrap: "nowrap",
              overflowX: "auto",
              gap: 6,
            }}
          >
            {chatSuggestions.map((sug, sIdx) => (
              <button
                key={sIdx}
                type="button"
                disabled={chatLoading}
                onClick={() => handleSendChatMessage(sug)}
                style={{
                  padding: "4px 10px",
                  fontSize: "0.72rem",
                  borderRadius: 14,
                  background: "#f1f5f9",
                  color: "#475569",
                  border: "1px solid #e2e8f0",
                  cursor: "pointer",
                  whiteSpace: "nowrap",
                  flexShrink: 0,
                }}
              >
                {sug}
              </button>
            ))}
          </div>

          {/* Input Box */}
          <div
            style={{
              padding: "10px 12px",
              background: "#ffffff",
              borderTop: "1px solid #e2e8f0",
              display: "flex",
              gap: 8,
              alignItems: "center",
            }}
          >
            <input
              type="text"
              value={chatInput}
              onChange={(e) => setChatInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter") {
                  e.preventDefault();
                  handleSendChatMessage();
                }
              }}
              placeholder="Ask Copilot anything..."
              style={{
                flex: 1,
                padding: "8px 12px",
                fontSize: "0.84rem",
                borderRadius: 8,
                border: "1px solid #cbd5e1",
                outline: "none",
              }}
            />
            <button
              type="button"
              disabled={chatLoading || !chatInput.trim()}
              onClick={() => handleSendChatMessage()}
              style={{
                padding: "8px 14px",
                borderRadius: 8,
                background: chatInput.trim() ? "#4f46e5" : "#94a3b8",
                color: "#ffffff",
                border: "none",
                fontWeight: 600,
                fontSize: "0.82rem",
                cursor: chatInput.trim() ? "pointer" : "default",
              }}
            >
              Send
            </button>
          </div>
        </div>
      )}

      {/* Attraction Remove / Replace Modal Dialog */}
      {attractionActionModal.open && (
        <div
          role="dialog"
          aria-modal="true"
          style={{
            position: "fixed",
            inset: 0,
            backgroundColor: "rgba(15, 23, 42, 0.6)",
            backdropFilter: "blur(4px)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            zIndex: 1050,
            padding: 16,
          }}
          onClick={() => {
            if (!actionExecuting) {
              setAttractionActionModal((prev) => ({ ...prev, open: false }));
            }
          }}
        >
          <div
            style={{
              backgroundColor: "#ffffff",
              borderRadius: 12,
              maxWidth: 580,
              width: "100%",
              maxHeight: "88vh",
              overflowY: "auto",
              boxShadow: "0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 8px 10px -6px rgba(0, 0, 0, 0.1)",
              display: "flex",
              flexDirection: "column",
            }}
            onClick={(e) => e.stopPropagation()}
          >
            {/* Modal Header */}
            <div
              style={{
                padding: "18px 24px",
                borderBottom: "1px solid #e2e8f0",
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center",
              }}
            >
              <div>
                <h3 style={{ margin: 0, fontSize: "1.2rem", color: "#0f172a" }}>
                  {attractionActionModal.mode === "choice"
                    ? `Remove Attraction: ${attractionActionModal.place?.name}`
                    : `Replace: ${attractionActionModal.place?.name}`}
                </h3>
                <p style={{ margin: "4px 0 0", fontSize: "0.84rem", color: "#64748b" }}>
                  Day {attractionActionModal.day} • {trip.destination}
                </p>
              </div>
              <button
                type="button"
                disabled={actionExecuting}
                onClick={() => setAttractionActionModal((prev) => ({ ...prev, open: false }))}
                style={{
                  background: "transparent",
                  border: "none",
                  fontSize: "1.25rem",
                  cursor: "pointer",
                  color: "#94a3b8",
                  padding: "4px 8px",
                  borderRadius: 6,
                }}
              >
                ✕
              </button>
            </div>

            {/* Modal Body */}
            <div style={{ padding: "20px 24px", flex: 1 }}>
              {attractionActionModal.mode === "choice" ? (
                <div>
                  <p style={{ marginTop: 0, marginBottom: 16, fontSize: "0.92rem", color: "#334155" }}>
                    How would you like to handle removing <strong>{attractionActionModal.place?.name}</strong> from Day {attractionActionModal.day}?
                  </p>

                  <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
                    {/* Choice A: Keep empty */}
                    <div
                      style={{
                        padding: 16,
                        borderRadius: 10,
                        border: "1px solid #e2e8f0",
                        background: "#f8fafc",
                        display: "flex",
                        flexDirection: "column",
                        gap: 8,
                      }}
                    >
                      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                        <span style={{ fontWeight: 700, fontSize: "0.95rem", color: "#0f172a" }}>
                          Option 1: Keep slot empty
                        </span>
                        <span style={{ fontSize: "0.75rem", background: "#e2e8f0", padding: "2px 8px", borderRadius: 12, fontWeight: 600, color: "#475569" }}>
                          No replacement
                        </span>
                      </div>
                      <p style={{ margin: 0, fontSize: "0.84rem", color: "#64748b", lineHeight: 1.4 }}>
                        Remove this attraction only. Does not auto-generate another stop. Day schedule, ordering, and unrelated activities remain preserved.
                      </p>
                      <button
                        type="button"
                        disabled={actionExecuting}
                        onClick={handleExecuteKeepEmpty}
                        style={{
                          alignSelf: "flex-start",
                          marginTop: 6,
                          padding: "8px 16px",
                          borderRadius: 6,
                          border: "1px solid #fca5a5",
                          background: "#fee2e2",
                          color: "#991b1b",
                          fontWeight: 600,
                          fontSize: "0.85rem",
                          cursor: actionExecuting ? "default" : "pointer",
                        }}
                      >
                        {actionExecuting ? "Removing..." : "Remove and Keep Slot Empty"}
                      </button>
                    </div>

                    {/* Choice B: Replace with another attraction */}
                    <div
                      style={{
                        padding: 16,
                        borderRadius: 10,
                        border: "1px solid #c7d2fe",
                        background: "#eef2ff",
                        display: "flex",
                        flexDirection: "column",
                        gap: 8,
                      }}
                    >
                      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                        <span style={{ fontWeight: 700, fontSize: "0.95rem", color: "#312e81" }}>
                          Option 2: Replace with another attraction
                        </span>
                        <span style={{ fontSize: "0.75rem", background: "#c7d2fe", padding: "2px 8px", borderRadius: 12, fontWeight: 600, color: "#3730a3" }}>
                          Discover alternatives
                        </span>
                      </div>
                      <p style={{ margin: 0, fontSize: "0.84rem", color: "#4338ca", lineHeight: 1.4 }}>
                        Browse verified alternative attractions for {trip.destination} (excluding already scheduled stops) to replace this slot in place.
                      </p>
                      <button
                        type="button"
                        disabled={actionExecuting}
                        onClick={() => {
                          setAttractionActionModal((prev) => ({ ...prev, mode: "replace" }));
                          if (attractionActionModal.place) {
                            fetchAlternatives(attractionActionModal.day, attractionActionModal.place.name);
                          }
                        }}
                        style={{
                          alignSelf: "flex-start",
                          marginTop: 6,
                          padding: "8px 16px",
                          borderRadius: 6,
                          border: "none",
                          background: "#4f46e5",
                          color: "#ffffff",
                          fontWeight: 600,
                          fontSize: "0.85rem",
                          cursor: "pointer",
                        }}
                      >
                        Browse Alternative Attractions →
                      </button>
                    </div>
                  </div>
                </div>
              ) : (
                /* Mode: replace */
                <div>
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 12 }}>
                    <span style={{ fontSize: "0.88rem", color: "#475569" }}>
                      Select an alternative attraction for this slot:
                    </span>
                    <button
                      type="button"
                      disabled={actionExecuting}
                      onClick={() => setAttractionActionModal((prev) => ({ ...prev, mode: "choice" }))}
                      style={{
                        background: "transparent",
                        border: "none",
                        color: "#4f46e5",
                        fontSize: "0.82rem",
                        fontWeight: 600,
                        cursor: "pointer",
                        padding: 0,
                      }}
                    >
                      ← Back to options
                    </button>
                  </div>

                  {alternativesLoading && (
                    <div style={{ padding: "30px 0", textAlign: "center", color: "#64748b" }}>
                      <div style={{ fontSize: "1.5rem", marginBottom: 8 }}>🔄</div>
                      <p style={{ margin: 0, fontSize: "0.9rem" }}>Finding suitable alternatives for {trip.destination}...</p>
                    </div>
                  )}

                  {alternativesError && (
                    <div
                      style={{
                        padding: 12,
                        borderRadius: 8,
                        background: "#fef2f2",
                        border: "1px solid #fecaca",
                        color: "#991b1b",
                        fontSize: "0.85rem",
                        marginBottom: 12,
                      }}
                    >
                      ⚠️ {alternativesError}
                    </div>
                  )}

                  {!alternativesLoading && !alternativesError && alternativesList.length === 0 && (
                    <div
                      style={{
                        padding: 24,
                        textAlign: "center",
                        background: "#f8fafc",
                        border: "1px dashed #cbd5e1",
                        borderRadius: 10,
                        color: "#475569",
                      }}
                    >
                      <p style={{ margin: "0 0 12px", fontSize: "0.92rem", fontWeight: 600, color: "#334155" }}>
                        No suitable alternative attractions available
                      </p>
                      <p style={{ margin: "0 0 16px", fontSize: "0.84rem", color: "#64748b" }}>
                        All known attractions for this destination are already in your itinerary or excluded. You can keep this slot empty instead.
                      </p>
                      <button
                        type="button"
                        disabled={actionExecuting}
                        onClick={handleExecuteKeepEmpty}
                        style={{
                          padding: "8px 18px",
                          borderRadius: 6,
                          border: "1px solid #cbd5e1",
                          background: "#ffffff",
                          color: "#334155",
                          fontWeight: 600,
                          fontSize: "0.85rem",
                          cursor: actionExecuting ? "default" : "pointer",
                        }}
                      >
                        {actionExecuting ? "Removing..." : "Keep Slot Empty"}
                      </button>
                    </div>
                  )}

                  {!alternativesLoading && alternativesList.length > 0 && (
                    <div style={{ display: "flex", flexDirection: "column", gap: 10, maxHeight: 380, overflowY: "auto", paddingRight: 4 }}>
                      {alternativesList.map((alt, aIdx) => (
                        <div
                          key={aIdx}
                          style={{
                            padding: "12px 14px",
                            borderRadius: 8,
                            border: "1px solid #e2e8f0",
                            background: "#ffffff",
                            display: "flex",
                            justifyContent: "space-between",
                            alignItems: "center",
                            gap: 12,
                            transition: "border-color 0.15s ease",
                          }}
                        >
                          <div style={{ flex: 1, minWidth: 0 }}>
                            <div style={{ display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap", marginBottom: 3 }}>
                              <strong style={{ fontSize: "0.92rem", color: "#0f172a" }}>{alt.name}</strong>
                              <span
                                style={{
                                  fontSize: "0.72rem",
                                  padding: "2px 7px",
                                  borderRadius: 10,
                                  background: "#f1f5f9",
                                  color: "#475569",
                                  fontWeight: 600,
                                }}
                              >
                                {alt.category}
                              </span>
                              {alt.score != null && alt.score > 0 && (
                                <span style={{ fontSize: "0.75rem", color: "#d97706", fontWeight: 600 }}>
                                  ★ {alt.score}
                                </span>
                              )}
                            </div>
                            <p
                              style={{
                                margin: 0,
                                fontSize: "0.8rem",
                                color: "#64748b",
                                lineHeight: 1.35,
                                overflow: "hidden",
                                textOverflow: "ellipsis",
                                whiteSpace: "normal",
                              }}
                            >
                              {alt.description}
                            </p>
                          </div>

                          <button
                            type="button"
                            disabled={actionExecuting}
                            onClick={() => handleExecuteReplace(alt)}
                            style={{
                              padding: "6px 14px",
                              borderRadius: 6,
                              border: "1px solid #c7d2fe",
                              background: "#eef2ff",
                              color: "#4338ca",
                              fontWeight: 600,
                              fontSize: "0.8rem",
                              cursor: actionExecuting ? "default" : "pointer",
                              whiteSpace: "nowrap",
                              flexShrink: 0,
                            }}
                          >
                            {actionExecuting ? "Updating..." : "Select & Replace"}
                          </button>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}
            </div>

            {/* Modal Footer */}
            <div
              style={{
                padding: "14px 24px",
                borderTop: "1px solid #e2e8f0",
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center",
                background: "#f8fafc",
                borderBottomLeftRadius: 12,
                borderBottomRightRadius: 12,
              }}
            >
              {attractionActionModal.mode === "replace" ? (
                <button
                  type="button"
                  disabled={actionExecuting}
                  onClick={handleExecuteKeepEmpty}
                  style={{
                    background: "transparent",
                    border: "none",
                    color: "#b91c1c",
                    fontSize: "0.82rem",
                    cursor: actionExecuting ? "default" : "pointer",
                    fontWeight: 600,
                    padding: 0,
                  }}
                >
                  Or keep slot empty instead
                </button>
              ) : (
                <div />
              )}

              <button
                type="button"
                disabled={actionExecuting}
                onClick={() => setAttractionActionModal((prev) => ({ ...prev, open: false }))}
                style={{
                  padding: "6px 16px",
                  borderRadius: 6,
                  border: "1px solid #cbd5e1",
                  background: "#ffffff",
                  color: "#475569",
                  fontSize: "0.85rem",
                  cursor: "pointer",
                  fontWeight: 500,
                }}
              >
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Place Information Detail Modal */}
      <PlaceDetailModal
        isOpen={placeDetailModal.isOpen}
        onClose={() => setPlaceDetailModal((prev) => ({ ...prev, isOpen: false }))}
        initialPlace={placeDetailModal.initialPlace}
        details={placeDetailModal.details}
        loading={placeDetailModal.loading}
        error={placeDetailModal.error}
      />

      {/* Collaboration Share Modal */}
      <TripShareModal
        tripId={tripId || ""}
        isOpen={showShareModal}
        onClose={() => setShowShareModal(false)}
        userRole={userRole}
      />

    </div>
  );
}
