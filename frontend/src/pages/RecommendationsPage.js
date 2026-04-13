import React, { useState, useEffect, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useNavigate, useParams } from 'react-router-dom';
import { generateRecommendation, replanRecommendation, getGroup } from '@/utils/api';
import { useAuth } from '@/contexts/AuthContext';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { Textarea } from '@/components/ui/textarea';
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Loader2, Sparkles, MapPin, IndianRupee, Clock, RefreshCw, ThumbsUp, AlertTriangle, Calendar, Wifi, WifiOff, Car } from 'lucide-react';
import { toast } from 'sonner';
import confetti from 'canvas-confetti';

const formatTime = (t) => {
  if (!t) return '?';
  const [hStr, mStr] = t.split(':');
  let h = parseInt(hStr, 10);
  const m = mStr || '00';
  const suffix = h >= 12 ? 'PM' : 'AM';
  if (h > 12) h -= 12;
  if (h === 0) h = 12;
  return `${h}:${m} ${suffix}`;
};

const ACTIVITY_ICONS = {
  dining: '🍽️',
  movie: '🎬',
  outdoor_relaxed: '🌿',
  outdoor_active: '⚡',
  cultural: '🏛️',
  entertainment: '🎉',
  free_time: '☕',
  arcade: '🎮',
  bowling: '🎳',
  'go-kart': '🏎️',
  karting: '🏎️',
  karaoke: '🎤',
  laser: '🔫',
  trampoline: '🤸',
  escape: '🔐',
  vr: '🥽',
  billiards: '🎱',
  gaming: '🕹️',
  mandi: '🍛',
  biryani: '🍛',
  haleem: '🫕',
  irani: '☕',
  waffle: '🧇',
  dessert: '🍰',
  street: '🥡',
};

const getActivityIcon = (activity) => {
  if (!activity) return '📍';
  const name = (activity.activity || activity.venue || '').toLowerCase();
  const type = (activity.type || '').toLowerCase();

  for (const [kw, icon] of Object.entries(ACTIVITY_ICONS)) {
    if (name.includes(kw)) return icon;
  }
  return ACTIVITY_ICONS[type] || '📍';
};

const MealBadge = ({ label }) => {
  if (!label) return null;
  const palette = {
    'Breakfast': 'bg-amber-50 text-amber-700 border-amber-200',
    'Brunch': 'bg-orange-50 text-orange-700 border-orange-200',
    'Lunch': 'bg-yellow-50 text-yellow-700 border-yellow-200',
    'Snacks / Tea Time': 'bg-lime-50 text-lime-700 border-lime-200',
    'Dinner': 'bg-purple-50 text-purple-700 border-purple-200',
    'Late Night Bites': 'bg-slate-100 text-slate-700 border-slate-200',
  };
  return (
    <span className={`inline-flex items-center gap-1 text-xs px-2 py-0.5 rounded-full font-semibold border ${palette[label] || 'bg-gray-100 text-gray-600 border-gray-200'}`}>
      🍴 {label}
    </span>
  );
};

const SourceBadge = ({ source }) => {
  if (source === 'system') return null;
  const isLive = source === 'live';
  return (
    <span className={`inline-flex items-center gap-1 text-xs px-2 py-0.5 rounded-full font-medium ${isLive
      ? 'bg-green-100 text-green-700 border border-green-200'
      : 'bg-amber-50 text-amber-700 border border-amber-200'
      }`}>
      {isLive ? <Wifi className="w-3 h-3" /> : <WifiOff className="w-3 h-3" />}
      {isLive ? 'Live' : 'Sample'}
    </span>
  );
};

const TravelConnector = ({ travelMin, travelNote }) => {
  if (!travelMin || travelMin === 0) return null;
  return (
    <div className="flex items-center gap-2 px-4 py-1.5 text-xs text-muted-foreground">
      <div className="flex-1 h-px bg-border/60 border-dashed border-t" />
      <span className="flex items-center gap-1.5 bg-muted/50 px-3 py-1 rounded-full shrink-0 border border-border/40">
        <Car className="w-3 h-3" />
        {travelNote || `~${travelMin} min travel`}
      </span>
      <div className="flex-1 h-px bg-border/60 border-dashed border-t" />
    </div>
  );
};

const FreeTimeCard = ({ activity, idx }) => (
  <motion.div
    key={`free-${idx}`}
    initial={{ opacity: 0, x: -20 }}
    animate={{ opacity: 1, x: 0 }}
    transition={{ delay: Math.min(idx * 0.08, 0.6) }}
  >
    <Card className="border-dashed border-2 border-primary/20 bg-muted/30">
      <CardContent className="pt-4 pb-4">
        <div className="flex items-start gap-3">
          <div className="w-10 h-10 rounded-full bg-muted flex items-center justify-center text-lg shrink-0">
            ☕
          </div>
          <div className="flex-1">
            <div className="flex items-center gap-2 mb-1 flex-wrap">
              <h3 className="font-outfit font-semibold text-muted-foreground">
                {activity.activity || 'Free Time'}
              </h3>
              <span className="text-xs px-2 py-0.5 rounded-full bg-muted text-muted-foreground border border-border">
                {activity.duration_minutes} min
              </span>
            </div>
            <p className="text-xs text-muted-foreground mb-2 flex items-center gap-1">
              <Clock className="w-3 h-3" />
              {formatTime(activity.arrival_time)} – {formatTime(activity.departure_time)}
            </p>
            <p className="text-sm text-muted-foreground italic mb-3">{activity.description}</p>
            {activity.suggestions && activity.suggestions.length > 0 && (
              <div className="flex flex-wrap gap-1.5">
                <span className="text-xs text-muted-foreground">Try:</span>
                {activity.suggestions.map((s, i) => (
                  <span
                    key={i}
                    className="text-xs px-2.5 py-1 rounded-full bg-primary/5 border border-primary/20 text-primary/80 font-medium"
                  >
                    {s}
                  </span>
                ))}
              </div>
            )}
          </div>
        </div>
      </CardContent>
    </Card>
  </motion.div>
);

const ActivityCard = ({ activity, idx, globalIdx }) => (
  <motion.div
    key={`${activity.activity}-${idx}`}
    initial={{ opacity: 0, x: -20 }}
    animate={{ opacity: 1, x: 0 }}
    transition={{ delay: Math.min(idx * 0.08, 0.6) }}
    whileHover={{ scale: 1.005 }}
    data-testid={`activity-${globalIdx}`}
  >
    <Card className="glass hover:shadow-xl transition-all">
      <CardContent className="pt-5">
        <div className="flex items-start justify-between gap-4">
          <div className="flex-1">
            <div className="flex items-center gap-3 mb-3">
              <div className="w-10 h-10 rounded-full bg-primary/20 flex items-center justify-center text-xl shrink-0 select-none">
                {getActivityIcon(activity)}
              </div>
              <div className="flex-1 min-w-0">
                <h3
                  className="text-lg font-outfit font-bold leading-tight"
                  data-testid={`activity-${globalIdx}-name`}
                >
                  {activity.activity}
                </h3>
                <div className="flex items-center gap-2 mt-0.5 flex-wrap">
                  <p className="text-sm text-muted-foreground capitalize">
                    {(activity.type || '').replace(/_/g, ' ')}
                  </p>
                  {activity.meal_label && <MealBadge label={activity.meal_label} />}
                  <SourceBadge source={activity.source} />
                </div>
              </div>
            </div>

            <div className="space-y-1.5 ml-13 pl-1">
              <div className="flex items-center gap-2 text-muted-foreground text-sm">
                <MapPin className="w-4 h-4 shrink-0" />
                <span data-testid={`activity-${globalIdx}-venue`}>{activity.venue}</span>
                {activity.distance_km != null && (
                  <span className="text-xs">({activity.distance_km} km away)</span>
                )}
              </div>

              <div className="flex items-center gap-2 text-muted-foreground text-sm">
                <Clock className="w-4 h-4 shrink-0" />
                <span data-testid={`activity-${globalIdx}-duration`}>
                  {activity.arrival_time && activity.departure_time
                    ? `${formatTime(activity.arrival_time)} – ${formatTime(activity.departure_time)}`
                    : `${activity.duration_minutes} min`}
                </span>
              </div>

              <div className="flex items-center gap-2 text-muted-foreground text-sm">
                <IndianRupee className="w-4 h-4 shrink-0" />
                <span data-testid={`activity-${globalIdx}-cost`}>
                  ₹{activity.estimated_cost} per person
                </span>
              </div>

              {activity.description && (
                <div className="mt-4 p-3 bg-primary/5 rounded-lg border border-primary/10 italic text-sm text-foreground/90">
                  <Sparkles className="w-3.5 h-3.5 inline-block mr-2 text-primary" />
                  {activity.description}
                </div>
              )}
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  </motion.div>
);

const ScheduleList = ({ activities, startGlobalIdx }) => {
  let globalIdx = startGlobalIdx;
  const items = [];

  activities.forEach((activity, idx) => {
    if (idx > 0 && activity.travel_time_min > 0) {
      items.push(
        <TravelConnector
          key={`travel-${idx}`}
          travelMin={activity.travel_time_min}
          travelNote={activity.travel_note}
        />
      );
    }

    if (activity.is_free_time) {
      items.push(<FreeTimeCard key={`free-${idx}`} activity={activity} idx={idx} />);
    } else {
      items.push(
        <ActivityCard
          key={`${activity.activity}-${idx}`}
          activity={activity}
          idx={idx}
          globalIdx={globalIdx}
        />
      );
    }
    globalIdx++;
  });

  return <>{items}</>;
};

const RecommendationsPage = () => {
  const { groupId } = useParams();
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [replanning, setReplanning] = useState(false);
  const [recommendation, setRecommendation] = useState(null);
  const [group, setGroup] = useState(null);
  const [adjustment, setAdjustment] = useState('');
  const [showReplanDialog, setShowReplanDialog] = useState(false);
  const { user } = useAuth();

  const hasFetched = useRef(false);

  useEffect(() => {
    if (hasFetched.current) return;
    hasFetched.current = true;

    const fetchRecommendation = async () => {
      try {
        const [recRes, groupRes] = await Promise.all([
          generateRecommendation({ group_id: groupId }),
          getGroup(groupId)
        ]);
        setRecommendation(recRes.data);
        setGroup(groupRes.data);
        confetti({ particleCount: 100, spread: 70, origin: { y: 0.6 } });
        toast.success('Perfect plan generated!');
      } catch (error) {
        toast.error('Failed to generate recommendations');
        console.error(error);
      } finally {
        setLoading(false);
      }
    };

    fetchRecommendation();
  }, [groupId]);

  const handleReplan = async () => {
    if (!adjustment.trim()) {
      toast.error("Please describe what you'd like to change");
      return;
    }
    setReplanning(true);
    hasFetched.current = false;
    try {
      const response = await replanRecommendation({
        recommendation_id: recommendation.id,
        adjustment,
      });
      setRecommendation({
        ...recommendation,
        id: response.data.id,
        schedule: response.data.schedule,
        reasoning: response.data.reasoning,
        diagnostics: response.data.diagnostics,
      });
      setShowReplanDialog(false);
      setAdjustment('');
      toast.success('Plan updated!');
    } catch (error) {
      toast.error('Failed to replan');
    } finally {
      setReplanning(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-background via-background to-primary/5 flex items-center justify-center">
        <div className="text-center space-y-4">
          <div className="relative mx-auto w-20 h-20">
            <Loader2 className="w-20 h-20 animate-spin text-primary" />
            <Sparkles className="w-8 h-8 text-primary absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2" />
          </div>
          <p className="text-xl font-outfit font-semibold text-muted-foreground">
            Creating your perfect plan...
          </p>
          <p className="text-sm text-muted-foreground">Searching nearby venues &amp; matching preferences</p>
        </div>
      </div>
    );
  }

  const schedule = recommendation?.schedule || [];
  const diags = recommendation?.diagnostics || {};
  const realActivities = schedule.filter(s => !s.is_free_time);
  const totalTime = realActivities.reduce((sum, act) => sum + (act.duration_minutes || 0), 0);
  const totalCost = realActivities.reduce((sum, act) => sum + (act.estimated_cost || 0), 0);
  const hasLive = schedule.some(s => s.source === 'live');

  const renderEmptyStateReason = () => {
    if (!recommendation || Object.keys(diags).length === 0) {
      return (
        <div className="space-y-2">
          <strong>Problem: Generation Failed</strong>
          <p className="text-sm">The AI failed to return a plan. This might be due to API limits or connectivity issues.</p>
        </div>
      );
    }
    const locationStr = String(diags.centroid?.lat || '');
    const isDefaultLoc = locationStr.includes('16.50') || locationStr.includes('40.71');
    if (isDefaultLoc) {
      return (
        <div className="space-y-2">
          <strong className="text-orange-600">Problem: Location Not Detected</strong>
          <p className="text-sm">
            We used a default location. Go back to the Lobby and click <strong>"Locate Me"</strong> to share your actual position.
          </p>
        </div>
      );
    }
    return 'Please try increasing your time window or budget.';
  };

  let globalCounter = 0;

  return (
    <div className="min-h-screen bg-gradient-to-br from-background via-background to-primary/5 p-6">
      <div className="max-w-5xl mx-auto py-8">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5 }}
        >
          <div className="flex items-center justify-between mb-8">
            <div>
              <h1
                className="text-4xl font-outfit font-black mb-2 flex items-center gap-3"
                data-testid="recommendations-title"
              >
                <Sparkles className="w-10 h-10 text-primary" />
                Your Perfect Plan
              </h1>
              <p className="text-muted-foreground">
                AI-curated activities for maximum enjoyment
              </p>
            </div>
            <Button variant="outline" onClick={() => navigate('/dashboard')} data-testid="back-to-dashboard-btn">
              New Group
            </Button>
          </div>

          {diags.missing_requested && diags.missing_requested.length > 0 && (
            <Alert className="mb-8 border-l-4 border-l-orange-500 bg-orange-50/50">
              <AlertTriangle className="h-4 w-4 text-orange-600" />
              <AlertTitle className="text-orange-800 font-bold">Heads up!</AlertTitle>
              <AlertDescription className="text-orange-700 italic">
                We couldn't find a live {diags.missing_requested.join(', ')} matching your timing and location.
                The schedule has been optimized around the best available alternatives!
              </AlertDescription>
            </Alert>
          )}

          {schedule.length === 0 && (
            <Alert variant="destructive" className="mb-8 border-l-4 border-l-red-500">
              <AlertTriangle className="h-4 w-4" />
              <AlertTitle>Activities Could Not Be Found</AlertTitle>
              <AlertDescription className="mt-2">{renderEmptyStateReason()}</AlertDescription>
            </Alert>
          )}

          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
            <Card className="glass">
              <CardContent className="pt-6">
                <Clock className="w-8 h-8 text-primary mb-2" />
                <p className="text-2xl font-bold" data-testid="total-time">
                  {Math.floor(totalTime / 60)}h {totalTime % 60}m
                </p>
                <p className="text-sm text-muted-foreground">Activity Time</p>
              </CardContent>
            </Card>
            <Card className="glass">
              <CardContent className="pt-6">
                <IndianRupee className="w-8 h-8 text-primary mb-2" />
                <p className="text-2xl font-bold" data-testid="total-cost">₹{totalCost}</p>
                <p className="text-sm text-muted-foreground">Estimated Cost</p>
              </CardContent>
            </Card>
            <Card className="glass">
              <CardContent className="pt-6">
                <MapPin className="w-8 h-8 text-primary mb-2" />
                <p className="text-2xl font-bold" data-testid="activity-count">{realActivities.length}</p>
                <p className="text-sm text-muted-foreground">Stops</p>
              </CardContent>
            </Card>
            <Card className="glass">
              <CardContent className="pt-6">
                <Sparkles className="w-8 h-8 text-primary mb-2" />
                <p className="text-2xl font-bold">
                  {hasLive ? (
                    <span className="flex items-center gap-1 text-green-600 text-lg">
                      <Wifi className="w-5 h-5" /> Live
                    </span>
                  ) : 'AI'}
                </p>
                <p className="text-sm text-muted-foreground">{hasLive ? 'Data' : 'Powered'}</p>
              </CardContent>
            </Card>
          </div>

          {schedule.length > 0 && (
            <div className="space-y-3 mb-8">
              <h2 className="text-2xl font-outfit font-bold">Your Schedule</h2>

              <AnimatePresence>
                <ScheduleList activities={schedule} startGlobalIdx={0} />
              </AnimatePresence>
            </div>
          )}

          {schedule.length > 0 && (
            <div className="flex flex-col sm:flex-row gap-4">
              {(group?.creator_id === user?.id || group?.creator_id === user?.user_id || localStorage.getItem('createdGroupId') === groupId) && (
                <Dialog open={showReplanDialog} onOpenChange={setShowReplanDialog}>
                  <DialogTrigger asChild>
                    <Button
                      variant="outline"
                      size="lg"
                      className="flex-1 rounded-full h-12"
                      data-testid="replan-btn"
                    >
                      <RefreshCw className="w-5 h-5 mr-2" />
                      Adjust Plan
                    </Button>
                  </DialogTrigger>
                  <DialogContent>
                    <DialogHeader>
                      <DialogTitle>Adjust Your Plan</DialogTitle>
                      <DialogDescription>
                        Tell us what you'd like to change, and we'll regenerate the schedule
                      </DialogDescription>
                    </DialogHeader>
                    <div className="space-y-4 mt-4">
                      <Textarea
                        placeholder="E.g., 'Add go-karting' or 'Replace the park with an arcade' or 'Prefer biryani over Italian'"
                        value={adjustment}
                        onChange={(e) => setAdjustment(e.target.value)}
                        rows={4}
                        data-testid="adjustment-input"
                      />
                      <Button
                        onClick={handleReplan}
                        disabled={replanning}
                        className="w-full rounded-full"
                        data-testid="replan-submit-btn"
                      >
                        {replanning ? (
                          <><Loader2 className="w-4 h-4 mr-2 animate-spin" /> Regenerating...</>
                        ) : (
                          'Regenerate Plan'
                        )}
                      </Button>
                    </div>
                  </DialogContent>
                </Dialog>
              )}

              <Button
                size="lg"
                className="flex-1 rounded-full h-12 shadow-lg shadow-primary/20"
                onClick={() => navigate(`/group/${groupId}/feedback/${recommendation?.id}`)}
                data-testid="approve-plan-btn"
              >
                <ThumbsUp className="w-5 h-5 mr-2" />
                Looks Great! Continue
              </Button>
            </div>
          )}

          {schedule.length === 0 && (
            <Button
              onClick={() => navigate(`/group/${groupId}`)}
              variant="outline"
              className="w-full"
            >
              Go Back and Edit Settings
            </Button>
          )}
        </motion.div>
      </div>
    </div>
  );
};

export default RecommendationsPage;