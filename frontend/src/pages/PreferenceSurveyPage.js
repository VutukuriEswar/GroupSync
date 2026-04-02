import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { useNavigate, useParams } from 'react-router-dom';
import { useAuth } from '@/contexts/AuthContext';
import { submitPreferences, getGroup } from '@/utils/api';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Label } from '@/components/ui/label';
import { RadioGroup, RadioGroupItem } from '@/components/ui/radio-group';
import { Slider } from '@/components/ui/slider';
import { Checkbox } from '@/components/ui/checkbox';
import { Progress } from '@/components/ui/progress';
import { Loader2, CircleCheck, Film, Utensils, Heart, Clock, Sparkles } from 'lucide-react';
import { toast } from 'sonner';

const PreferenceSurveyPage = () => {
  const { groupId } = useParams();
  const navigate = useNavigate();
  const { user, isGuest } = useAuth();
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [group, setGroup] = useState(null);
  const [currentQuestion, setCurrentQuestion] = useState(0);
  const [preferences, setPreferences] = useState({});

  const questions = [

    {
      id: 'movie_genres',
      category: 'movies',
      icon: Film,
      type: 'checkbox',
      question: '🎬 What movie genres do you enjoy?',
      description: 'Select all that interest you - helps us match movies to your taste',
      options: ['Action', 'Comedy', 'Drama', 'Horror', 'Romance', 'Thriller', 'Sci-Fi', 'Animation', 'Documentary', 'Family', 'Adventure', 'Mystery', 'Fantasy'],
      rlMapping: 'genres'
    },
    {
      id: 'movie_language',
      category: 'movies',
      icon: Film,
      type: 'checkbox',
      question: '🎬 Any language preferences for movies?',
      description: 'Select languages you\'re comfortable watching',
      options: ['English', 'Hindi', 'Telugu', 'Tamil', 'Malayalam', 'Korean', 'Japanese', 'Any Language'],
      rlMapping: 'language_preference'
    },
    {
      id: 'movie_format',
      category: 'movies',
      icon: Film,
      type: 'radio',
      question: '🎬 Premium movie experience?',
      description: 'Are you open to IMAX/4DX formats?',
      options: ['Standard only (budget-friendly)', 'Open to premium formats', 'Prefer premium experience'],
      rlMapping: 'movie_format_preference'
    },

    {
      id: 'cuisines',
      category: 'dining',
      icon: Utensils,
      type: 'checkbox',
      question: '🍴 What cuisines do you enjoy?',
      description: 'Select all your favorites - helps us find the perfect restaurant',
      options: ['Indian', 'North Indian', 'South Indian', 'Chinese', 'Italian', 'Mexican', 'Thai', 'Japanese', 'Korean', 'Mediterranean', 'Continental', 'Seafood', 'American'],
      rlMapping: 'cuisines'
    },
    {
      id: 'dietary',
      category: 'dining',
      icon: Utensils,
      type: 'checkbox',
      question: '🍴 Any dietary preferences?',
      description: 'Help us find suitable dining options',
      options: ['Vegetarian', 'Vegan', 'Non-Vegetarian', 'Halal', 'Gluten-Free', 'No restrictions'],
      rlMapping: 'dietary_restrictions'
    },
    {
      id: 'dining_style',
      category: 'dining',
      icon: Utensils,
      type: 'radio',
      question: '🍴 What dining ambiance do you prefer?',
      description: 'Casual eatery or fine dining?',
      options: ['Street food / Casual', 'Cafe / Quick bites', 'Casual dining restaurant', 'Fine dining experience', 'Any is fine'],
      rlMapping: 'dining_style'
    },

    {
      id: 'vibes',
      category: 'activities',
      icon: Heart,
      type: 'checkbox',
      question: '✨ What kind of experience are you looking for?',
      description: 'Select all that match your mood - shapes the entire day\'s vibe',
      options: ['Relaxing', 'Adventurous', 'Romantic', 'Family-friendly', 'Budget-friendly', 'Luxurious', 'Social', 'Cultural', 'Active', 'Entertaining'],
      rlMapping: 'vibes'
    },
    {
      id: 'energy_level',
      category: 'activities',
      icon: Sparkles,
      type: 'slider',
      question: '⚡ How active do you want to be?',
      description: '1 = Chilled out, 5 = Full energy',
      min: 1,
      max: 5,
      labels: ['Couch Potato', 'Chill Explorer', 'Moderate Activity', 'Active Adventurer', 'Maximum Energy'],
      rlMapping: 'energy_level'
    },
    {
      id: 'novelty',
      category: 'activities',
      icon: Sparkles,
      type: 'radio',
      question: '🆕 Want to try something new?',
      description: 'New experiences or familiar favorites?',
      options: ['Surprise me! Something totally new', 'Mix of new and familiar', 'Stick to my comfort zone', 'Only my favorite activities'],
      rlMapping: 'novelty_preference'
    },
    {
      id: 'group_dynamic',
      category: 'activities',
      icon: Heart,
      type: 'radio',
      question: '👥 Group activity preference?',
      description: 'How do you want to interact?',
      options: ['Just my close friends', 'Open to meeting new people', 'Mixed social settings', 'Solo within a group'],
      rlMapping: 'social_preference'
    },
    {
      id: 'exploration_preference',
      category: 'activities',
      icon: Sparkles,
      type: 'radio',
      question: '🎲 How adventurous are you with recommendations today?',
      description: 'Controls whether the AI (RL) sticks to popular choices or discovers new gems',
      options: [
        'Stick to what’s popular and safe',
        'A good mix of popular and new',
        'Surprise me with hidden gems!'
      ],
      rlMapping: 'exploration_factor'
    },

    {
      id: 'time_slots',
      category: 'time',
      icon: Clock,
      type: 'checkbox',
      question: '🕐 When do you prefer activities?',
      description: 'Select your preferred time slots',
      options: ['Morning (6AM - 12PM)', 'Afternoon (12PM - 5PM)', 'Evening (5PM - 9PM)', 'Night (9PM - 12AM)', 'Late Night (After 12AM)'],
      rlMapping: 'preferred_time_slots'
    },
    {
      id: 'meal_preference',
      category: 'time',
      icon: Clock,
      type: 'radio',
      question: '🍽️ Is food a main part of the plan?',
      description: 'Should meals drive the schedule?',
      options: ['Yes, meals are the main event', 'Food is important but flexible', 'Snacks are fine', 'Food is not a priority'],
      rlMapping: 'meal_priority'
    },
    {
      id: 'travel_tolerance',
      category: 'time',
      icon: Clock,
      type: 'radio',
      question: '🚗 Maximum travel between activities?',
      description: 'How far are you willing to go?',
      options: ['Walking distance only (<2km)', 'Short ride (<10km)', 'Anywhere in the city', 'Day trip willing'],
      rlMapping: 'travel_tolerance'
    },

    ...(!isGuest() ? [
      {
        id: 'accessibility',
        category: 'additional',
        icon: Heart,
        type: 'radio',
        question: '♿ Any accessibility needs?',
        description: 'Help us find suitable venues',
        options: ['Need wheelchair accessibility', 'Some mobility considerations', 'No specific needs'],
        rlMapping: 'accessibility_needs'
      },
      {
        id: 'competition',
        category: 'additional',
        icon: Sparkles,
        type: 'radio',
        question: '🎮 Competitive or cooperative?',
        description: 'For games and activities',
        options: ['I love competition!', 'Friendly competition is fun', 'Prefer cooperative games', 'No competitive activities'],
        rlMapping: 'competition_preference'
      }
    ] : [])
  ];

  const progress = ((currentQuestion + 1) / questions.length) * 100;

  useEffect(() => {
    const init = async () => {
      try {
        const response = await getGroup(groupId);
        setGroup(response.data);

        if (response.data.status !== 'preferences') {
          toast.info('Waiting for the host to start the session...');
          navigate(`/group/${groupId}`);
          return;
        }

        const storedId = localStorage.getItem('current_member_id');
        const userId = user?.id || user?.user_id;
        const myId = storedId || userId;

        if (!isGuest() && user && user.default_preferences && Object.keys(user.default_preferences).length > 0) {
          toast.success("Using your saved profile preferences...", { duration: 1500 });

          await submitPreferences({
            group_id: groupId,
            user_id: myId,
            session_id: myId,
            preferences: user.default_preferences,
            is_registered: true
          });

          navigate(`/group/${groupId}/waiting`);
          return;
        }

        setLoading(false);

      } catch (error) {
        console.error(error);
        toast.error('Failed to load group');
        navigate('/dashboard');
      }
    };
    init();
  }, [groupId, navigate, user, isGuest]);

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
    const storedId = localStorage.getItem('current_member_id');
    const userId = user?.id || user?.user_id;
    const myId = storedId || userId;

    if (!myId) {
      toast.error("Identification error. Please refresh.");
      navigate('/dashboard');
      return;
    }

    try {

      const rlPreferences = transformPreferencesForRL(preferences);

      await submitPreferences({
        group_id: groupId,
        user_id: myId,
        session_id: myId,
        preferences: rlPreferences,
        is_registered: !!userId
      });
      toast.success('Preferences submitted!');
      navigate(`/group/${groupId}/waiting`);
    } catch (error) {
      console.error(error);
      toast.error('Failed to submit preferences');
    } finally {
      setSubmitting(false);
    }
  };

  const transformPreferencesForRL = (prefs) => {
    const transformed = { ...prefs };

    if (prefs.movie_genres) {
      transformed.genres = prefs.movie_genres.map(g => g.toLowerCase().replace('-', ''));
    }

    if (prefs.cuisines) {
      transformed.cuisines = prefs.cuisines.map(c => c.toLowerCase().replace(' ', '_'));
    }

    if (prefs.vibes) {
      transformed.vibes = prefs.vibes.map(v => v.toLowerCase().replace('-', '_'));
    }

    if (prefs.time_slots) {
      transformed.preferred_time_slots = prefs.time_slots.map(t => {
        if (t.includes('Morning')) return 'morning';
        if (t.includes('Afternoon')) return 'afternoon';
        if (t.includes('Evening')) return 'evening';
        if (t.includes('Late Night')) return 'late_night';
        return 'night';
      });
    }

    transformed.energy_level = prefs.energy_level || 3;
    transformed.novelty_preference = prefs.novelty || 'Mix of new and familiar';

    const expMap = {
      'Stick to what’s popular and safe': 0.5,
      'A good mix of popular and new': 1.5,
      'Surprise me with hidden gems!': 3.0
    };
    transformed.exploration_factor = expMap[prefs.exploration_preference] || 1.5;

    return transformed;
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
  const CategoryIcon = currentQ.icon;

  const categoryColors = {
    movies: 'text-purple-500 bg-purple-50',
    dining: 'text-orange-500 bg-orange-50',
    activities: 'text-green-500 bg-green-50',
    time: 'text-blue-500 bg-blue-50',
    additional: 'text-pink-500 bg-pink-50'
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-background via-background to-primary/5 p-6">
      <div className="max-w-3xl mx-auto py-8">
        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}>
          <div className="mb-8">
            <div className="flex items-center justify-between mb-2">
              <span className="text-sm font-medium" data-testid="question-counter">
                Question {currentQuestion + 1} of {questions.length}
              </span>
              <span className="text-sm text-muted-foreground">{Math.round(progress)}% Complete</span>
            </div>
            <Progress value={progress} className="h-2" data-testid="survey-progress" />
          </div>

          <div className="flex flex-wrap gap-2 mb-6">
            {['movies', 'dining', 'activities', 'time'].map((cat, idx) => {
              const catQuestions = questions.filter(q => q.category === cat);
              const currentIndex = questions.findIndex(q => q.id === currentQ.id);
              const catStartIndex = questions.findIndex(q => q.category === cat);
              const catEndIndex = catStartIndex + catQuestions.length - 1;
              const isComplete = currentIndex > catEndIndex;
              const isCurrent = currentIndex >= catStartIndex && currentIndex <= catEndIndex;

              return (
                <div
                  key={cat}
                  className={`px-3 py-1 rounded-full text-xs font-medium transition-colors ${isComplete ? 'bg-primary text-white' :
                    isCurrent ? 'bg-primary/20 text-primary border-2 border-primary' :
                      'bg-muted text-muted-foreground'
                    }`}
                >
                  {cat.charAt(0).toUpperCase() + cat.slice(1)}
                  {isComplete && ' ✓'}
                </div>
              );
            })}
          </div>

          <Card className="glass border-2">
            <CardHeader>
              <div className="flex items-center gap-3 mb-2">
                <div className={`w-12 h-12 rounded-xl flex items-center justify-center ${categoryColors[currentQ.category]}`}>
                  <CategoryIcon className="w-6 h-6" />
                </div>
                <div>
                  <CardTitle className="text-2xl font-outfit font-bold" data-testid="current-question">
                    {currentQ.question}
                  </CardTitle>
                  <CardDescription className="text-base">
                    {currentQ.description}
                  </CardDescription>
                </div>
              </div>
            </CardHeader>
            <CardContent className="space-y-6">
              {currentQ.type === 'radio' && (
                <RadioGroup value={currentAnswer} onValueChange={handleAnswer}>
                  <div className="space-y-3">
                    {currentQ.options.map((option, idx) => (
                      <motion.div
                        key={idx}
                        whileHover={{ scale: 1.01 }}
                        whileTap={{ scale: 0.99 }}
                        className={`flex items-center space-x-3 p-4 rounded-xl cursor-pointer transition-all ${currentAnswer === option
                          ? 'bg-primary/10 border-2 border-primary'
                          : 'glass hover:border-primary/50 border-2 border-transparent'
                          }`}
                        onClick={() => handleAnswer(option)}
                      >
                        <RadioGroupItem value={option} id={`${currentQ.id}-${idx}`} data-testid={`option-${idx}`} />
                        <Label htmlFor={`${currentQ.id}-${idx}`} className="flex-1 cursor-pointer text-base">
                          {option}
                        </Label>
                      </motion.div>
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
                  <div className="flex flex-col items-center gap-2">
                    <span className="text-3xl font-bold text-primary" data-testid="slider-value">
                      {currentAnswer || 3}
                    </span>
                    <span className="text-lg text-center">
                      {currentQ.labels[(currentAnswer || 3) - 1]}
                    </span>
                  </div>
                  <div className="flex justify-between text-sm text-muted-foreground">
                    <span>{currentQ.labels[0]}</span>
                    <span>{currentQ.labels[currentQ.labels.length - 1]}</span>
                  </div>
                </div>
              )}

              {currentQ.type === 'checkbox' && (
                <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
                  {currentQ.options.map((option, idx) => {
                    const isChecked = Array.isArray(currentAnswer) && currentAnswer.includes(option);
                    return (
                      <motion.div
                        key={idx}
                        whileHover={{ scale: 1.02 }}
                        whileTap={{ scale: 0.98 }}
                        className={`flex items-center space-x-3 p-4 rounded-xl cursor-pointer transition-all ${isChecked
                          ? 'bg-primary/10 border-2 border-primary'
                          : 'glass hover:border-primary/50 border-2 border-transparent'
                          }`}
                        onClick={() => {
                          const current = Array.isArray(currentAnswer) ? currentAnswer : [];
                          if (isChecked) {
                            handleAnswer(current.filter(o => o !== option));
                          } else {
                            handleAnswer([...current, option]);
                          }
                        }}
                      >
                        <Checkbox
                          id={`${currentQ.id}-${idx}`}
                          checked={isChecked}
                          data-testid={`checkbox-${idx}`}
                        />
                        <Label htmlFor={`${currentQ.id}-${idx}`} className="cursor-pointer text-sm">
                          {option}
                        </Label>
                      </motion.div>
                    );
                  })}
                </div>
              )}

              <div className="flex gap-4 pt-6">
                <Button
                  variant="outline"
                  onClick={handlePrevious}
                  disabled={currentQuestion === 0}
                  className="flex-1 rounded-full h-12"
                >
                  Previous
                </Button>
                <Button
                  onClick={handleNext}
                  disabled={!currentAnswer || (Array.isArray(currentAnswer) && currentAnswer.length === 0) || submitting}
                  className="flex-1 rounded-full h-12 shadow-lg shadow-primary/20"
                >
                  {submitting ? (
                    <><Loader2 className="w-4 h-4 mr-2 animate-spin" /> Submitting...</>
                  ) : currentQuestion === questions.length - 1 ? (
                    <><CircleCheck className="w-4 h-4 mr-2" /> Submit</>
                  ) : (
                    'Next'
                  )}
                </Button>
              </div>

              {currentQ.category !== 'movies' && currentQ.category !== 'dining' && (
                <button
                  type="button"
                  onClick={handleNext}
                  className="w-full text-center text-sm text-muted-foreground hover:text-primary transition-colors py-2"
                >
                  Skip this question
                </button>
              )}
            </CardContent>
          </Card>
        </motion.div>
      </div>
    </div>
  );
};

export default PreferenceSurveyPage;
