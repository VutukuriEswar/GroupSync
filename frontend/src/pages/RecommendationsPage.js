import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useNavigate, useParams } from 'react-router-dom';
import { generateRecommendation, getRecommendation, replanRecommendation } from '@/utils/api';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Textarea } from '@/components/ui/textarea';
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Loader2, Sparkles, MapPin, IndianRupee, Clock, RefreshCw, ThumbsUp, AlertTriangle, Globe } from 'lucide-react';
import { toast } from 'sonner';
import confetti from 'canvas-confetti';

const RecommendationsPage = () => {
  const { groupId } = useParams();
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [replanning, setReplanning] = useState(false);
  const [recommendation, setRecommendation] = useState(null);
  const [adjustment, setAdjustment] = useState('');
  const [showReplanDialog, setShowReplanDialog] = useState(false);

  useEffect(() => {
    const fetchRecommendation = async () => {
      try {
        const response = await generateRecommendation({ group_id: groupId });
        setRecommendation(response.data);

        confetti({
          particleCount: 100,
          spread: 70,
          origin: { y: 0.6 }
        });

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
      toast.error('Please describe what you\'d like to change');
      return;
    }

    setReplanning(true);
    try {
      const response = await replanRecommendation({
        recommendation_id: recommendation.id,
        adjustment: adjustment
      });

      setRecommendation({
        ...recommendation,
        id: response.data.id,
        schedule: response.data.schedule,
        reasoning: response.data.reasoning,
        diagnostics: response.data.diagnostics
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
        <div className="text-center">
          <Loader2 className="w-16 h-16 animate-spin text-primary mx-auto mb-4" />
          <p className="text-xl font-outfit font-semibold text-muted-foreground">Creating your perfect plan...</p>
        </div>
      </div>
    );
  }

  const schedule = recommendation?.schedule || [];
  const totalTime = schedule.reduce((sum, act) => sum + act.duration_minutes, 0) || 0;
  const totalCost = schedule.reduce((sum, act) => sum + act.estimated_cost, 0) || 0;
  const diags = recommendation?.diagnostics || {};

  const renderEmptyStateReason = () => {

    if (!recommendation || Object.keys(diags).length === 0) {
      return (
        <div className="space-y-2">
          <strong>Problem: Generation Failed</strong>
          <p className="text-sm">The AI failed to return a plan. This might be due to API limits or connectivity issues.</p>
        </div>
      );
    }

    const locationStr = diags.location || "";
    const isDefaultNYC = locationStr.includes("40.71");

    const timeWindow = parseInt(diags.time_window || 0);
    if (timeWindow < 90) {
      return (
        <div className="space-y-2">
          <strong>Problem: Time Window Too Short</strong>
          <p className="text-sm">You only provided {diags.time_window}. Travel + Activities require at least 2 hours usually.</p>
        </div>
      );
    }

    if (isDefaultNYC) {
      return (
        <div className="space-y-2">
          <strong className="text-orange-600">Problem: Location Permission Not Given</strong>
          <p className="text-sm">
            We are using a default location (New York) because your browser location wasn't detected.
            <br /><span className="text-xs">Go back to the Lobby and click "Locate Me" to fix this.</span>
          </p>
        </div>
      );
    }

    if (diags.raw_activities_count === 0) {
      return (
        <div className="space-y-2">
          <strong>Problem: External APIs Returned Nothing</strong>
          <div className="bg-slate-100 p-2 rounded text-xs mt-1 font-mono">
            <div>Search Location: {locationStr}</div>
            <div>TMDB Movies: {diags.tmdb_count || 0} found</div>
            <div>OSM Venues: {diags.osm_count || 0} found</div>
            <div>Weather: {diags.weather_status || "Unknown"}</div>
          </div>
          <p className="text-sm text-muted-foreground">
            {(diags.filtered_count === 0 && diags.raw_activities_count > 0)
              ? "Activities were found, but your Budget or Rating filters removed them all."
              : "Connectivity or API Key issues."}
          </p>
        </div>
      );
    }

    return "Please try increasing time or budget.";
  };

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
              <h1 className="text-4xl font-outfit font-black mb-2 flex items-center gap-3" data-testid="recommendations-title">
                <Sparkles className="w-10 h-10 text-primary" />
                Your Perfect Plan
              </h1>
              <p className="text-muted-foreground">
                AI-curated activities for maximum group enjoyment
              </p>
            </div>
            <Button
              variant="outline"
              onClick={() => navigate('/dashboard')}
              data-testid="back-to-dashboard-btn"
            >
              New Group
            </Button>
          </div>

          <Card className="glass mb-8 border-2 border-primary/20" data-testid="reasoning-card">
            <CardHeader>
              <CardTitle className="text-xl font-outfit font-bold">Why This Plan?</CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-lg leading-relaxed">{recommendation?.reasoning || "No reasoning provided."}</p>
            </CardContent>
          </Card>

          {schedule.length === 0 && (
            <Alert variant="destructive" className="mb-8 border-l-4 border-l-red-500">
              <AlertTriangle className="h-4 w-4" />
              <AlertTitle>Activities Could Not Be Found</AlertTitle>
              <AlertDescription className="mt-2">
                {renderEmptyStateReason()}
              </AlertDescription>
            </Alert>
          )}

          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
            <Card className="glass">
              <CardContent className="pt-6">
                <Clock className="w-8 h-8 text-primary mb-2" />
                <p className="text-2xl font-bold" data-testid="total-time">{Math.floor(totalTime / 60)}h {totalTime % 60}m</p>
                <p className="text-sm text-muted-foreground">Total Time</p>
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
                <p className="text-2xl font-bold" data-testid="activity-count">{schedule.length}</p>
                <p className="text-sm text-muted-foreground">Activities</p>
              </CardContent>
            </Card>
            <Card className="glass">
              <CardContent className="pt-6">
                <Sparkles className="w-8 h-8 text-primary mb-2" />
                <p className="text-2xl font-bold">AI</p>
                <p className="text-sm text-muted-foreground">Powered</p>
              </CardContent>
            </Card>
          </div>

          <div className="space-y-4 mb-8">
            <h2 className="text-2xl font-outfit font-bold">Your Schedule</h2>
            <AnimatePresence>
              {schedule.length > 0 ? schedule.map((activity, idx) => (
                <motion.div
                  key={idx}
                  initial={{ opacity: 0, x: -20 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: idx * 0.1 }}
                  whileHover={{ scale: 1.02 }}
                  data-testid={`activity-${idx}`}
                >
                  <Card className="glass hover:shadow-xl transition-all">
                    <CardContent className="pt-6">
                      <div className="flex items-start justify-between">
                        <div className="flex-1">
                          <div className="flex items-center gap-3 mb-3">
                            <div className="w-10 h-10 rounded-full bg-primary/20 flex items-center justify-center font-bold text-lg">
                              {activity.order}
                            </div>
                            <div>
                              <h3 className="text-xl font-outfit font-bold" data-testid={`activity-${idx}-name`}>
                                {activity.activity}
                              </h3>
                              <p className="text-sm text-muted-foreground capitalize">{activity.type.replace('_', ' ')}</p>
                            </div>
                          </div>
                          <div className="space-y-2 ml-13">
                            <div className="flex items-center gap-2 text-muted-foreground">
                              <MapPin className="w-4 h-4" />
                              <span data-testid={`activity-${idx}-venue`}>{activity.venue}</span>
                              <span className="text-sm">({activity.distance_km} km away)</span>
                            </div>
                            <div className="flex items-center gap-2 text-muted-foreground">
                              <Clock className="w-4 h-4" />
                              <span data-testid={`activity-${idx}-duration`}>{activity.duration_minutes} minutes</span>
                            </div>
                            <div className="flex items-center gap-2 text-muted-foreground">
                              <IndianRupee className="w-4 h-4" />
                              <span data-testid={`activity-${idx}-cost`}>₹{activity.estimated_cost} per person</span>
                            </div>
                          </div>
                        </div>
                      </div>
                    </CardContent>
                  </Card>
                </motion.div>
              )) : (
                <div className="text-center py-8 text-muted-foreground italic">
                  No activities scheduled.
                </div>
              )}
            </AnimatePresence>
          </div>

          {schedule.length > 0 && (
            <div className="flex flex-col sm:flex-row gap-4">
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
                      placeholder="E.g., 'Add more outdoor activities' or 'Replace movie with something active'"
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