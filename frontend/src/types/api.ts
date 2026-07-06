export type Location = {
  lat: number;
  lng: number;
};

export type TimeWindow = {
  start: string;
  end: string;
};

export type Order = {
  orderId: string;
  userId: string;
  merchantId: string;
  title: string;
  category: string;
  status: "unused" | "used" | "refunded" | "expired";
  validFrom: string;
  validUntil: string;
  usableWeekdays: number[];
  usableTimeWindows: TimeWindow[];
  price: number;
  value: number;
  needsReservation: boolean;
  tags: string[];
  imageUrl: string;
};

export type Merchant = {
  merchantId: string;
  name: string;
  category: string;
  address: string;
  location: Location;
  rating: number;
  avgPrice: number;
  status: "normal" | "closed" | "abnormal";
  reservationRequired: boolean;
  reservationRisk: number;
  queueRisk: number;
  imageUrl: string;
  businessHoursId: string;
};

export type RuleCheck = {
  ruleId: string;
  passed: boolean;
  severity: "info" | "warning" | "blocking";
  message: string;
  affectedEntityId?: string;
};

export type ScoreBreakdown = {
  total: number;
  factors: Record<string, number>;
  penalties: Record<string, number>;
  notes: string[];
};

export type TripAction = {
  type: "use_order" | "reservation_hint" | "view" | "browse" | "purchase_placeholder" | "ai_followup";
  label: string;
  enabled: boolean;
  disabledReason?: string;
};

export type Availability = {
  isOpen: boolean;
  isOrderUsable: boolean;
  warnings: string[];
};

export type TripNode = {
  nodeId: string;
  type: "order" | "interest" | "hotspot" | "nearby";
  title: string;
  reason: string;
  entityId: string;
  name: string;
  category: string;
  location: Location;
  imageUrl: string;
  plannedStartTime: string;
  plannedEndTime: string;
  distanceFromPreviousMeters: number;
  durationFromPreviousMinutes: number;
  action: TripAction;
  availability: Availability;
  score: ScoreBreakdown;
};

export type RouteSegment = {
  fromNodeId: string;
  toNodeId: string;
  distanceMeters: number;
  durationMinutes: number;
  polyline: Location[];
};

export type RouteSummary = {
  totalDistanceMeters: number;
  totalDurationMinutes: number;
  polyline: Location[];
  segments: RouteSegment[];
};

export type TripSummary = {
  title: string;
  text: string;
  entryCopy: string;
  llmProvider: string;
};

export type TripPlan = {
  planId: string;
  status: "success";
  targetDateLabel: string;
  timeWindow: TimeWindow;
  userLocation: Location;
  summary: TripSummary;
  anchorOrderId: string;
  nodes: TripNode[];
  route: RouteSummary;
  score: ScoreBreakdown;
  ruleChecks: RuleCheck[];
  debug: Record<string, unknown>;
  planningLogFile?: string;
  readablePlanningLogFile?: string;
};

export type PlanningFailure = {
  status: "failed";
  failureCode: string;
  message: string;
  ruleChecks: RuleCheck[];
  planningLogFile?: string;
  readablePlanningLogFile?: string;
};

export type TripPlanResponse = TripPlan | PlanningFailure;

export type PlanningProgressEvent = {
  traceId?: string;
  sequence?: number;
  time?: string;
  eventType?: string;
  progressTitle?: string;
  detailText?: string;
};

export type AssistantEntry = {
  visible: boolean;
  title: string;
  subtitle: string;
  copy: string;
  entryCopySource: "rules_precheck" | "hidden";
  eligibleOrderCount: number;
  totalUnusedOrderCount: number;
  executableRouteCount: number;
  candidateOrderIds: string[];
  reasonCodes: string[];
  ruleChecks: RuleCheck[];
  dataMode: "mock";
};

export type TrackingEvent = {
  eventName: string;
  userId: string;
  planId?: string;
  payload?: Record<string, unknown>;
};

export type TripActionExecuteRequest = {
  planId?: string;
  nodeId: string;
  actionType: string;
  entityId: string;
  userId?: string;
};

export type TripActionExecuteResponse = {
  ok: boolean;
  status: "recorded" | "not_integrated";
  message: string;
  nextStep?: string;
};
