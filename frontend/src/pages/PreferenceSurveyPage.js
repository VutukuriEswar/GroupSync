import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { useNavigate, useParams } from 'react-router-dom';
import { useAuth } from '@/contexts/AuthContext';
import { submitPreferences, getGroup, getGroupMembers } from '@/utils/api';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Label } from '@/components/ui/label';
import { RadioGroup, RadioGroupItem } from '@/components/ui/radio-group';
import { Slider } from '@/components/ui/slider';
import { Checkbox } from '@/components/ui/checkbox';
import { Progress } from '@/components/ui/progress';
import { Loader2, CheckCircle2, Users } from 'lucide-react';
import { toast } from 'sonner';

const PreferenceSurveyPage = () => {
  const { groupId } = useParams();
  const navigate = useNavigate();
  const { user, isGuest, sessionId } = useAuth();
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [group, setGroup] = useState(null);
  const [currentQuestion, setCurrentQuestion] = useState(0);
  const [preferences, setPreferences] = useState({});

  // Comprehensive Questions
  const guestQuestions = [
    { id: 'energy_level', type: 'slider', question: 'What is your energy level today?', min: 1, max: 5, labels: ['Completely Exhausted', 'Super Hyper'] },
    { id: 'social_preference', type: 'radio', question: 'Who do you want to interact with?', options: ['Just my close friends', 'Meeting new people', 'Mixed crowd', 'Nobody (Solo activities)'] },
    { id: 'entertainment_primary', type: 'checkbox', question: 'What type of entertainment do you enjoy most?', options: ['Live Events (Concerts/Sports)', 'Cinema/Movies', 'Gaming', 'Dining Out', 'Nature/Outdoors', 'Art & Culture', 'Workshops/Classes'] },
    { id: 'movie_genre', type: 'checkbox', question: 'Favorite Movie Genres?', options: ['Action', 'Horror', 'Comedy', 'Sci-Fi', 'Romance', 'Documentary', 'Animation'] },
    { id: 'gaming_preference', type: 'radio', question: 'Gaming Interest?', options: ['Hardcore Gamer', 'Casual Mobile Games', 'Board/Card Games', 'Not interested'] },
    { id: 'music_vibe', type: 'radio', question: 'Music preference for the activity?', options: ['Live Band/DJ', 'Chill Background Music', 'Silence/Nature Sounds', 'Upbeat Pop'] },
    { id: 'budget_sensitivity', type: 'slider', question: 'How much are you willing to spend per person?', min: 1, max: 5, labels: ['Free Only', '$$$$ No Limit'] },
    { id: 'travel_radius', type: 'radio', question: 'How far are you willing to travel?', options: ['Walking distance (<2km)', 'Short Uber (<10km)', 'Anywhere in the city', 'Day trip willing'] },
    { id: 'weather_tolerance', type: 'radio', question: 'Weather Preference?', options: ['Strictly Indoors', 'Covered Outdoors', 'Rain or Shine', 'Snow activities welcome'] },
    { id: 'food_priority', type: 'radio', question: 'Is food a main part of the plan?', options: ['Yes, Dinner is the event', 'Snacks are fine', 'Just Drinks', 'Food not important'] },
    { id: 'novelty_seek', type: 'radio', question: 'Do you want to try something NEW?', options: ['Never tried before, surprise me', 'Tried but rare', 'My favorite classics only', 'Comfort zone please'] },
    { id: 'physical_activity', type: 'slider', question: 'Desired Physical Exertion?', min: 1, max: 5, labels: ['Couch Potato', 'Olympic Athlete'] },
    { id: 'crowd_tolerance', type: 'radio', question: 'Crowd Comfort?', options: ['Avoid crowds', 'Small groups only', 'Busy is okay', 'The more, the merrier'] },
    { id: 'time_of_day', type: 'checkbox', question: 'Best times?', options: ['Early Morning', 'Mid-Day', 'Afternoon', 'Evening', 'Late Night'] }
  ];

  const registeredQuestions = [
    ...guestQuestions,
    { id: 'alcohol_pref', type: 'radio', question: 'Alcohol?', options: ['Yes, please', 'Mocktails only', 'Sober environment preferred'] },
    { id: 'specific_diet', type: 'checkbox', question: 'Dietary Restrictions?', options: ['Vegan', 'Vegetarian', 'Gluten Free', 'Nut Allergy', 'Halal', 'Kosher', 'None'] },
    { id: 'learning_style', type: 'radio', question: 'Do you want to learn something?', options: ['Yes, teach me a skill', 'Yes, learn about history/art', 'No, just for fun'] },
    { id: 'competition_level', type: 'radio', question: 'Competitive Nature?', options: ['Destroy my friends', 'Friendly competition', 'Cooperative only', 'No games'] },
    { id: 'photography', type: 'radio', question: 'Insta-worthy?', options: ['Every corner must be aesthetic', 'A few nice spots', 'Dont care about photos'] },
    { id: 'transport_mode', type: 'checkbox', question: 'Available Transport?', options: ['Personal Car', 'Public Transit', 'Uber/Lyft', 'Walking/Biking'] },
    { id: 'kids_friendly', type: 'radio', question: 'Child friendly requirements?', options: ['Need kid activities', 'Teens okay', 'Adults only'] },
    { id: 'accessibility', type: 'radio', question: 'Mobility considerations?', options: ['Need full accessibility', 'Some stairs okay', 'No issues'] },
    { id: 'planning_style', type: 'radio', question: 'Spontaneity?', options: ['Every minute planned', 'Rough plan, go with flow', 'Totally random'] }
  ];

  const questions = isGuest() ? guestQuestions : registeredQuestions;
  const progress = ((currentQuestion + 1) / questions.length) * 100;

  useEffect(() => {
    const fetchGroup = async () => {
      try {
        const response = await getGroup(groupId);
        setGroup(response.data);
      } catch (error) {
        toast.error('Failed to load group');
        navigate('/dashboard');
      } finally {
        setLoading(false);
      }
    };
    fetchGroup();
  }, [groupId, navigate]);

  const handleAnswer = (value) => {
    const question = questions[currentQuestion];
    setPreferences({ ...preferences, [question.id]: value });
  };

  const handleNext = () => {
    if (currentQuestion < questions.length - 1) {
      setCurrentQuestion(currentQuestion + 1);
    } else {
      handleSubmit();
    }
  };

  const handlePrevious = () => {
    if (currentQuestion > 0) {
      setCurrentQuestion(currentQuestion - 1);
    }
  };

  const handleSubmit = async () => {
    setSubmitting(true);
    try {
      await submitPreferences({
        group_id: groupId,
        user_id: user?.id,
        session_id: sessionId,
        preferences: preferences,
        is_registered: !isGuest()
      });
      toast.success('Preferences submitted!');
      navigate(`/group/${groupId}/waiting`);
    } catch (error) {
      toast.error('Failed to submit preferences');
    } finally {
      setSubmitting(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-background via-background to-primary/5 flex items-center justify-center">
        <Loader2 className="w-12 h-12 animate-spin text-primary" />
      </div>
    );
  }

  const currentQ = questions[currentQuestion];
  const currentAnswer = preferences[currentQ.id];

  return (
    <div className="min-h-screen bg-gradient-to-br from-background via-background to-primary/5 p-6">
      <div className="max-w-3xl mx-auto py-8">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5 }}
        >
          <div className="mb-8">
            <div className="flex items-center justify-between mb-2">
              <span className="text-sm font-medium" data-testid="question-counter">
                Question {currentQuestion + 1} of {questions.length}
              </span>
              <span className="text-sm text-muted-foreground">{Math.round(progress)}% Complete</span>
            </div>
            <Progress value={progress} className="h-2" data-testid="survey-progress" />
          </div>

          <Card className="glass border-2">
            <CardHeader>
              <CardTitle className="text-2xl font-outfit font-bold" data-testid="current-question">
                {currentQ.question}
              </CardTitle>
              {currentQuestion === 0 && (
                <CardDescription className="text-base">
                  {isGuest() ? '14 quick questions' : '23 detailed questions'} to help us find the perfect activities for your group
                </CardDescription>
              )}
            </CardHeader>
            <CardContent className="space-y-6">
              {currentQ.type === 'radio' && (
                <RadioGroup value={currentAnswer} onValueChange={handleAnswer}>
                  <div className="space-y-3">
                    {currentQ.options.map((option, idx) => (
                      <div key={idx} className="flex items-center space-x-3 glass p-4 rounded-xl hover:border-primary transition-colors">
                        <RadioGroupItem value={option} id={`${currentQ.id}-${idx}`} data-testid={`option-${idx}`} />
                        <Label htmlFor={`${currentQ.id}-${idx}`} className="flex-1 cursor-pointer text-base">
                          {option}
                        </Label>
                      </div>
                    ))}
                  </div>
                </RadioGroup>
              )}

              {currentQ.type === 'slider' && (
                <div className="space-y-6">
                  <Slider
                    value={[currentAnswer || 3]}
                    onValueChange={([value]) => handleAnswer(value)}
                    min={currentQ.min}
                    max={currentQ.max}
                    step={1}
                    className="w-full"
                    data-testid="slider-input"
                  />
                  <div className="flex justify-between text-sm text-muted-foreground">
                    <span>{currentQ.labels[0]}</span>
                    <span className="text-lg font-bold text-primary" data-testid="slider-value">{currentAnswer || 3}</span>
                    <span>{currentQ.labels[1]}</span>
                  </div>
                </div>
              )}

              {currentQ.type === 'checkbox' && (
                <div className="grid grid-cols-2 gap-3">
                  {currentQ.options.map((option, idx) => (
                    <div key={idx} className="flex items-center space-x-3 glass p-4 rounded-xl">
                      <Checkbox
                        id={`${currentQ.id}-${idx}`}
                        checked={Array.isArray(currentAnswer) && currentAnswer.includes(option)}
                        onCheckedChange={(checked) => {
                          const current = Array.isArray(currentAnswer) ? currentAnswer : [];
                          if (checked) {
                            handleAnswer([...current, option]);
                          } else {
                            handleAnswer(current.filter(o => o !== option));
                          }
                        }}
                        data-testid={`checkbox-${idx}`}
                      />
                      <Label htmlFor={`${currentQ.id}-${idx}`} className="cursor-pointer text-base">
                        {option}
                      </Label>
                    </div>
                  ))}
                </div>
              )}

              <div className="flex gap-4 pt-6">
                <Button
                  variant="outline"
                  onClick={handlePrevious}
                  disabled={currentQuestion === 0}
                  className="flex-1 rounded-full h-12"
                  data-testid="previous-btn"
                >
                  Previous
                </Button>
                <Button
                  onClick={handleNext}
                  disabled={!currentAnswer || submitting}
                  className="flex-1 rounded-full h-12 shadow-lg shadow-primary/20"
                  data-testid="next-btn"
                >
                  {submitting ? (
                    <><Loader2 className="w-4 h-4 mr-2 animate-spin" /> Submitting...</>
                  ) : currentQuestion === questions.length - 1 ? (
                    <><CheckCircle2 className="w-4 h-4 mr-2" /> Submit</>
                  ) : (
                    'Next'
                  )}
                </Button>
              </div>
            </CardContent>
          </Card>
        </motion.div>
      </div>
    </div>
  );
};

export default PreferenceSurveyPage;