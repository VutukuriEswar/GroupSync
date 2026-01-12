import React, { useState } from 'react';
import { motion } from 'framer-motion';
import { useNavigate, useParams } from 'react-router-dom';
import { submitFeedback } from '@/utils/api';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Textarea } from '@/components/ui/textarea';
import { Label } from '@/components/ui/label';
import { Slider } from '@/components/ui/slider';
import { Star, Sparkles, Loader2 } from 'lucide-react';
import { toast } from 'sonner';
import confetti from 'canvas-confetti';

const FeedbackPage = () => {
  const { groupId, recommendationId } = useParams();
  const navigate = useNavigate();
  const [submitting, setSubmitting] = useState(false);
  const [formData, setFormData] = useState({
    overall_satisfaction: 5,
    comments: ''
  });

  const handleSubmit = async (e) => {
    e.preventDefault();
    setSubmitting(true);

    try {
      await submitFeedback({
        recommendation_id: recommendationId,
        group_id: groupId,
        overall_satisfaction: formData.overall_satisfaction,
        activity_ratings: [],
        comments: formData.comments
      });

      confetti({
        particleCount: 200,
        spread: 100,
        origin: { y: 0.6 }
      });

      toast.success('Thank you for your feedback!');

      setTimeout(() => {
        navigate('/dashboard');
      }, 2000);
    } catch (error) {
      toast.error('Failed to submit feedback');
    } finally {
      setSubmitting(false);
    }
  };

  const satisfactionLabels = {
    1: 'Poor',
    2: 'Fair',
    3: 'Good',
    4: 'Great',
    5: 'Excellent'
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-background via-background to-primary/5 flex items-center justify-center p-6">
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
        className="w-full max-w-2xl"
      >
        <Card className="glass border-2">
          <CardHeader className="text-center">
            <div className="w-20 h-20 rounded-full bg-primary/10 flex items-center justify-center mx-auto mb-4">
              <Sparkles className="w-10 h-10 text-primary" />
            </div>
            <CardTitle className="text-3xl font-outfit font-bold" data-testid="feedback-title">
              How Was Your Experience?
            </CardTitle>
            <CardDescription className="text-base">
              Your feedback helps us improve recommendations for everyone
            </CardDescription>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleSubmit} className="space-y-8">
              {/* Overall Satisfaction */}
              <div className="space-y-4">
                <Label className="text-lg font-medium">Overall Satisfaction</Label>
                <div className="space-y-4">
                  {/* Star Rating Visual */}
                  <div className="flex justify-center gap-2">
                    {[1, 2, 3, 4, 5].map((rating) => (
                      <motion.button
                        key={rating}
                        type="button"
                        whileHover={{ scale: 1.2 }}
                        whileTap={{ scale: 0.9 }}
                        onClick={() => setFormData({ ...formData, overall_satisfaction: rating })}
                        className="focus:outline-none"
                        data-testid={`star-rating-${rating}`}
                      >
                        <Star
                          className={`w-12 h-12 transition-colors ${rating <= formData.overall_satisfaction
                              ? 'fill-primary text-primary'
                              : 'text-muted'
                            }`}
                        />
                      </motion.button>
                    ))}
                  </div>

                  {/* Slider */}
                  <div className="space-y-3">
                    <Slider
                      value={[formData.overall_satisfaction]}
                      onValueChange={([value]) => setFormData({ ...formData, overall_satisfaction: value })}
                      min={1}
                      max={5}
                      step={1}
                      className="w-full"
                      data-testid="satisfaction-slider"
                    />
                    <div className="text-center">
                      <p className="text-2xl font-bold text-primary" data-testid="satisfaction-label">
                        {satisfactionLabels[formData.overall_satisfaction]}
                      </p>
                    </div>
                  </div>
                </div>
              </div>

              {/* Comments */}
              <div className="space-y-2">
                <Label htmlFor="comments" className="text-lg font-medium">Additional Comments (Optional)</Label>
                <Textarea
                  id="comments"
                  placeholder="What did you love? What could be better? Any suggestions?"
                  value={formData.comments}
                  onChange={(e) => setFormData({ ...formData, comments: e.target.value })}
                  rows={5}
                  className="text-base"
                  data-testid="comments-input"
                />
              </div>

              {/* Submit */}
              <Button
                type="submit"
                disabled={submitting}
                className="w-full rounded-full text-lg h-12 shadow-lg shadow-primary/20"
                data-testid="submit-feedback-btn"
              >
                {submitting ? (
                  <><Loader2 className="w-5 h-5 mr-2 animate-spin" /> Submitting...</>
                ) : (
                  <>Submit Feedback</>
                )}
              </Button>

              <p className="text-center text-sm text-muted-foreground">
                Your feedback is anonymous and helps improve the AI for future groups
              </p>
            </form>
          </CardContent>
        </Card>
      </motion.div>
    </div>
  );
};

export default FeedbackPage;