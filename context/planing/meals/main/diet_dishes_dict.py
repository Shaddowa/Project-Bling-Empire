from fractions import Fraction
from .data_classes.category import Category
from .data_classes.difficulty import DifficultyLevel
from .data_classes.spice_level import SpiceLevel
from .data_classes.unit import MeasurementUnit, GeneralUnit
from .utils.unit_converter import UnitConverter
from ...meals.main.data_classes.dish import Dish
from ...meals.main.data_classes.ingredients import Vegetable, Spice, Measurement, Condiment, Fruit, Meat, Bread, Dairy, \
    Dough, Seed, Other, Noodle

diet_dishes = [
    Dish(
        title="Pork, Pineapple, and Onion Skewers",
        image_url="pork_pineapple_onion_skewers.png",
        category=[Category("Skewers"), Category("Low Carb")],
        time=30,
        budget_friendly=None,
        region=None,
        spicy=SpiceLevel.NO_SPICE,
        difficulty=DifficultyLevel.EASY,
        description="Sweet pineapple threaded between bites of savory pork provides a sweet, juicy contrast.",
        nutritional_info="Per serving: About 308 cal, 11 g fat (2.5 g sat), 65 mg chol, 897 mg sodium, 24 g carb, 2 g fiber, 17 g sugar (6 g added sugar), 29 g protein",
        ingredients=[
            Spice("Ginger", "Grated", UnitConverter.convert(Measurement(Fraction(1, 2), MeasurementUnit.CUP)), None),
            Spice("Sugar", "White", Measurement(2, MeasurementUnit.TBSP), None),
            Spice("Kosher salt", "to taste", None, None),
            Spice("Pepper", "to taste", None, None),
            Spice("Jalapeño", "Sliced", None, None),
            Vegetable("Bell Pepper", "Mixed colors", UnitConverter.convert(Measurement(8, MeasurementUnit.OZ)), None),
            Vegetable("Red Onion", "Halved crosswise", Measurement(1, GeneralUnit.WHOLE), None),
            Fruit("Pineapple", "Peeled and cored", Measurement(Fraction(1, 2), GeneralUnit.HALF), None),
            Meat("Pork loin", "trimmed", UnitConverter.convert(Measurement(1, MeasurementUnit.LB)), None),
            Condiment("Soy Sauce", "reduced sodium", UnitConverter.convert(Measurement(Fraction(1, 2), MeasurementUnit.CUP)), None),
            Condiment("Mirin", "Regular", UnitConverter.convert(Measurement(Fraction(1, 2), MeasurementUnit.CUP)), None),
            Condiment("Sake", "Regular", UnitConverter.convert(Measurement(Fraction(1, 2), MeasurementUnit.CUP)), None),
            Condiment("Olive oil", "Extra Virgin", Measurement(2, MeasurementUnit.TBSP), None)
        ],
        recipe={
            1: "In a small saucepan, combine sake, mirin, soy sauce, sugar, and ginger. "
               "Simmer, stirring occasionally, until sugar has dissolved, 3 minutes."
               "Gently simmer, until thickened slightly and coats back of spoon, 12 minutes more.",

            2: "Meanwhile, cut pork and pineapple into 1 pieces. Cut onion into wedges. "
               "In a bowl, toss pork, pineapple, and vegetables with oil and ½ tsp. each salt and pepper.",

            3: "Heat grill to medium. Thread pork, pineapple, and vegetables onto skewers."
               "Grill, turning occasionally, until pork is cooked through, 8 to 10 minutes, basting with sauce during"
               "last 5 minutes of grilling. Serve topped with sliced jalapeños..",
        }
    ),
    Dish(
        title="Salmon Burgers with Greek Yogurt Sauce",
        image_url="salmon_burgers_greek_yogurt_sauce.png",
        category=[Category("Salmon Burger"), Category("Low Carb")],
        time=30,
        budget_friendly=None,
        region=None,
        spicy=SpiceLevel.MILD,
        difficulty=DifficultyLevel.EASY,
        description="Skip the frozen patties and make your own salmon burger, starting with the fresh fish. You'll get the same rich, juicy flavor without any preservatives.",
        nutritional_info="Per serving: 379 cal, 13 g fat (3.5 g sat), 34 g protein, 580 mg sodium, 32 g carb, 8.5 g sugars (0 g added sugars), 3 g fiber",
        ingredients=[
            Condiment("Egg", "large", Measurement(1, GeneralUnit.WHOLE), None),
            Meat("Salmon fillet", "finely chopped", UnitConverter.convert(Measurement(1, MeasurementUnit.LB)), None),
            Vegetable("Scallions", "chopped", Measurement(2, GeneralUnit.WHOLE), None),
            Spice("Jalapeño", "finely chopped", Measurement(1, GeneralUnit.WHOLE), None),
            Vegetable("Cilantro", "chopped and divided", Measurement(3, MeasurementUnit.TBSP), None),
            Spice("Kosher salt", "to taste", None, None),
            Spice("Pepper", "to taste", None, None),
            Condiment("Olive oil", "for cooking", Measurement(1, MeasurementUnit.TBSP), None),
            Condiment("Greek yogurt", "plain", UnitConverter.convert(Measurement(Fraction(1, 2), MeasurementUnit.CUP)), None),
            Spice("Lime zest", "fresh", Measurement(1, MeasurementUnit.TSP), None),
            Condiment("Lime juice", "fresh", Measurement(2, MeasurementUnit.TBSP), None),
            Bread("Brioche buns", "toasted", Measurement(4, GeneralUnit.WHOLE), None),
            Vegetable("Bibb lettuce leaves", GeneralUnit.WHOLE, Measurement(8, GeneralUnit.LEAVES), None),
            Vegetable("Persian cucumbers", "shaved lengthwise", Measurement(2, GeneralUnit.WHOLE), None),
            Vegetable("Broccoli or radish sprouts", "fresh", UnitConverter.convert(Measurement(2, MeasurementUnit.CUP)), None)
        ],
        recipe={
            1: "In a medium bowl, beat egg until frothy. Fold in salmon, scallions, jalapeño, 2 tbsp. cilantro, 1/2 tsp. salt, and 1/4 tsp. pepper.",
            2: f"Heat oil in a large nonstick skillet on medium. Spoon 4 mounds of salmon mixture (about {UnitConverter.convert(Measurement(Fraction(1, 2), MeasurementUnit.CUP)).unit.value} each)"
               "into skillet and flatten into patties. Cook until golden brown, 2 minutes per side.",
            3: "Meanwhile, in a bowl, combine yogurt, lime zest and juice, remaining 1 tbsp. cilantro, and 1/4 tsp."
               "each salt and pepper. Spread on buns. Top bottom buns with lettuce, salmon patties, cucumber, and sprouts; sandwich with top buns."
        }
    ),
    Dish(
        title="Portobello Mushroom Tostadas",
        image_url=None,
        category=[Category("Vegetarian"), Category("Low Carb")],
        time=25,
        budget_friendly=None,
        region=None,
        spicy=SpiceLevel.MILD,
        difficulty=DifficultyLevel.EASY,
        description="Mushrooms brushed with tangy BBQ and smoky adobo sauces build lingering heat, while creamy guacamole cools things down. Dinner with heaps of flavor is done.",
        nutritional_info="Per serving: 335 cal, 15 g fat (3 g sat), 7 g protein, 767 mg sodium, 46 g carb, 14.5 g sugars (0 g added sugars), 7 g fiber",
        ingredients=[
            Vegetable("Red onion", "thinly sliced", Measurement(Fraction(1, 2), GeneralUnit.SMALL), None),
            Spice("Jalapeño", "half sliced, other half finely chopped", Measurement(1, GeneralUnit.WHOLE), None),
            Condiment("Lime juice", "fresh", Measurement(2.5, MeasurementUnit.TBSP), None),
            Spice("Sugar", "Pinch", None, None),
            Spice("Kosher salt", "to taste", None, None),
            Dough("Corn tortillas", "regular", Measurement(8, GeneralUnit.WHOLE), None),
            Condiment("Olive oil", "for brushing", Measurement(1, MeasurementUnit.TBSP), None),
            Condiment("Barbecue sauce", "regular", UnitConverter.convert(Measurement(Fraction(1, 2), MeasurementUnit.CUP)), None),
            Spice("Chipotles in adobo", "chopped, plus adobo sauce", Measurement(1, MeasurementUnit.TSP), None),
            Vegetable("Portobello mushroom caps", "gills removed", Measurement(4, GeneralUnit.WHOLE), None),
            Vegetable("Avocado", "halved and scooped", Measurement(1, GeneralUnit.WHOLE), None),
            Vegetable("Cilantro leaves", "finely chopped", UnitConverter.convert(Measurement(Fraction(1, 4), MeasurementUnit.CUP)), None),
            Vegetable("Radishes", "thinly sliced", Measurement(3, GeneralUnit.WHOLE), None),
            Dairy("Cotija cheese", "crumbled", UnitConverter.convert(Measurement(Fraction(1, 4), MeasurementUnit.CUP)), None)
        ],
        recipe={
            1: "Heat oven to 450°F. In a small bowl, combine onion, sliced jalapeño, 1 tbsp. lime juice, sugar, and pinch of salt.",
            2: "Divide tortillas between 2 rimmed baking sheets. Using 1 tbsp. olive oil, brush both sides of each tortilla with oil. Bake until brown and crisp, 3 to 4 minutes per side.",
            3: "Heat broiler. In a small bowl, combine barbecue sauce, chipotles, and adobo.",
            4: "Place portobellos cap side down on a rimmed baking sheet; broil 5 minutes. Flip, brush caps with some adobo glaze; broil until browned in spots, 2 to 3 minutes. Brush with additional glaze, transfer to a cutting board and slice.",
            5: "Meanwhile, in a medium bowl, combine avocado, cilantro, chopped jalapeño, remaining 1 1/2 tbsp. lime juice, and 1/2 tsp. salt; mash until creamy. Spread on tostadas, then top with portobellos, radishes, pickled onion, jalapeño, and cotija."
        }
    ),
    Dish(
        title="Grilled Pizza with Cottage Cheese and Tomatoes",
        image_url="caprese_pizza.png",
        category=[Category("Vegetarian"), Category("Low Carb")],
        time=25,
        budget_friendly=None,
        region=None,
        spicy=SpiceLevel.NO_SPICE,
        difficulty=DifficultyLevel.MEDIUM,
        description="A delightful grilled pizza topped with a smooth cottage cheese mixture, heirloom and cherry tomatoes, and fresh arugula salad.",
        nutritional_info="Per serving: 468 cal, 21 g fat (4.5 g sat), 10 mg chol, 842 mg sodium, 49 g carb, 9 g fiber, 9 g sugar (3.5 g added sugar), 19 g protein",
        ingredients=[
            Dough("Whole wheat pizza dough", "at room temp for 1 hr if refrigerated", None, None),
            Dairy("Whole milk cottage cheese", "regular", UnitConverter.convert(Measurement(Fraction(3, 4), MeasurementUnit.CUP)), None),
            Dairy("Parmesan", "finely grated", UnitConverter.convert(Measurement(1, MeasurementUnit.OZ)), None),
            Vegetable("Basil leaves", "chopped", UnitConverter.convert(Measurement(Fraction(1, 4), MeasurementUnit.CUP)), None),
            Spice("Lemon zest", "fresh", Measurement(1, MeasurementUnit.TSP), None),
            Condiment("Lemon juice", "fresh", Measurement(1, MeasurementUnit.TBSP), None),
            Vegetable("Heirloom tomatoes", "sliced", Measurement(3, GeneralUnit.MEDIUM), None),
            Vegetable("Cherry tomatoes", GeneralUnit.WHOLE, UnitConverter.convert(Measurement(Fraction(1, 2), MeasurementUnit.CUP)), None),
            Condiment("Olive oil", "for brushing", Measurement(1, MeasurementUnit.TBSP), None),
            Condiment("Honey", "regular", Measurement(Fraction(1, 2), MeasurementUnit.TSP), None),
            Spice("Kosher salt", "to taste", None, None),
            Spice("Pepper", "to taste", None, None),
            Vegetable("Shallot", "chopped", Measurement(1, GeneralUnit.SMALL), None),
            Vegetable("Baby arugula", "fresh", UnitConverter.convert(Measurement(4, MeasurementUnit.CUP)), None)
        ],
        recipe={
            1: "Prepare and grill pizza dough; transfer to cutting board.",
            2: "In a food processor, puree cottage cheese until smooth, then pulse in Parmesan. Transfer to bowl and fold in basil and lemon zest. Spread cheese mixture onto pizza crust and top with tomatoes.",
            3: "In a large bowl, whisk together olive oil, lemon juice, honey, 1/4 tsp salt, and 1/8 tsp pepper to dissolve; stir in shallot. Add arugula and toss to coat. Top tomatoes with arugula salad and sprinkle with additional Parmesan, if desired."
        }
    ),
    Dish(
        title="Sriracha Chicken Lettuce Wraps (Paleo, Keto)",
        image_url="sriracha_chicken_lettuce_wraps.png",
        category=[Category("Paleo"), Category("Keto")],
        time=30,
        budget_friendly=None,
        region="Asian",
        spicy=SpiceLevel.MILD,
        difficulty=DifficultyLevel.EASY,
        description="Quick and flavorful Sriracha Chicken Lettuce Wraps that are easy to assemble and perfect for lunch or dinner.",
        nutritional_info="Per serving: 297 cal, 11 g fat (2 g sat), 162 mg cholesterol, 696 mg sodium, 15 g carb, 1 g fiber, 11 g sugar, 33 g protein",
        ingredients=[
            Condiment("Avocado oil", "or your favorite cooking oil", Measurement(1, MeasurementUnit.TBSP), None),
            Vegetable("Onion", "diced", Measurement(Fraction(1, 2), GeneralUnit.WHOLE), None),
            Meat("Chicken thighs", "skinless boneless, cut into bite sized pieces", UnitConverter.convert(Measurement(1.5, MeasurementUnit.LB)), None),
            Spice("Garlic", "minced", Measurement(3, GeneralUnit.CLOVES), None),
            Vegetable("Celery", "chopped", UnitConverter.convert(Measurement(1, MeasurementUnit.CUP)), None),
            Vegetable("Carrot", "shredded", Measurement(1, GeneralUnit.WHOLE), None),
            Condiment("Sugar free sriracha sauce", "regular", Measurement(3, MeasurementUnit.TBSP), None),
            Condiment("Coconut aminos", "or soy sauce, for keto", Measurement(3, MeasurementUnit.TBSP), None),
            Condiment("Honey", "or monkfruit sweetener, for keto", Measurement(2, MeasurementUnit.TBSP), None),
            Vegetable("Bib, butter, or romaine lettuce", "leaves", Measurement(12, GeneralUnit.WHOLE), None),
            Seed("Sesame seeds", "for garnish", None, None),
            Vegetable("Green onions", "chopped, for garnish", None, None)
        ],
        recipe={
            1: "Heat oil in a large skillet over medium high heat.",
            2: "Add onion and sauté for 3 minutes.",
            3: "Add chicken and cook, stirring for about 10 minutes, until browned on all sides.",
            4: "Stir in garlic, celery, and carrots, and cook for 3 minutes.",
            5: "Pour in sriracha, coconut aminos, and honey, and stir until the sauce is thickened and the chicken is coated.",
            6: "Remove from heat, and garnish with sesame seeds and green onions.",
            7: "Serve in lettuce leaves."
        }
    ),
    Dish(
        title="Crockpot Seafood Ramen Soup",
        image_url="crockpot_seafood_ramen_soup.png",
        category=[Category("Seafood"), Category("Soup")],
        time=130,
        budget_friendly=None,
        region="Asian",
        spicy=SpiceLevel.MILD,
        difficulty=DifficultyLevel.MEDIUM,
        description="A simple noodle recipe that pairs your favorite seafood with ramen noodles, perfect for slow cooking in a crockpot.",
        nutritional_info="Per serving: 297 kcal",
        ingredients=[
            Meat("Seafood", "raw or cooked", UnitConverter.convert(Measurement(1, MeasurementUnit.LB)), None),
            Noodle("Ramen", "uncooked", Measurement(178, MeasurementUnit.ML), None),
            Other("Broth", "vegetable, seafood, or chicken", Measurement(948, MeasurementUnit.ML), None),
            Other("Water", "regular", Measurement(474, MeasurementUnit.ML), None),
            Vegetable("Green onions", "sliced", Measurement(2, GeneralUnit.WHOLE), None),
            Condiment("Soy sauce", "low sodium", Measurement(59, MeasurementUnit.ML), None),
            Condiment("Rice vinegar", "regular", Measurement(59, MeasurementUnit.ML), None),
            Spice("Garlic", "minced", Measurement(2, GeneralUnit.CLOVES), None),
            Spice("Ginger", "minced", Measurement(1, MeasurementUnit.TBSP), None),
            Vegetable("Bok choy", "chopped", Measurement(76, MeasurementUnit.GRAMS), None),
            Vegetable("Mushrooms", "sliced", Measurement(86, MeasurementUnit.GRAMS), None),
            Vegetable("Carrots", "shredded", Measurement(128, MeasurementUnit.GRAMS), None),
            Condiment("Sesame oil", "regular", Measurement(Fraction(1, 4), MeasurementUnit.TSP), None),
            Spice("Salt", "or more to taste", Measurement(1, MeasurementUnit.TSP), None),
            Spice("Pepper", "to taste", Measurement(Fraction(1, 4), MeasurementUnit.TSP), None),
            Spice("Red pepper flakes", "optional", Measurement(Fraction(1, 4), MeasurementUnit.TSP), None)
        ],
        recipe={
            1: "Add broth, water, green onions, soy sauce, rice vinegar, garlic, ginger, mushrooms, carrots, sesame oil, salt, pepper, and red pepper flakes (if using) to the slow cooker. Stir to mix well.",
            2: "Cook on HIGH for 2 3 hours, or on LOW for 4 6 hours.",
            3: "Stir in the seafood, ramen, and bok choy. Cook for an additional 15 30 minutes.",
            4: "For Instant Pot: Add broth, water, green onions, soy sauce, rice vinegar, garlic, ginger, mushrooms, carrots, sesame oil, salt, pepper, and red pepper flakes (if using) to the Instant Pot. Stir to mix well.",
            5: "Close lid and seal valve. Set to high pressure and cook for 12 minutes. When cooking time is complete, quick release the pressure.",
            6: "Open the lid. Add the seafood, ramen, and bok choy. Close lid and cook an additional 5 10 minutes on the WARM setting."
        }
    ),
    # Dish(
    #     title="Chicken Taco Soup",
    #     image_url="healthy_chicken_taco_soup.png",
    #     category=[Category("Soup"), Category("Chicken")],
    #     time=40,
    #     budget_friendly=None,
    #     region="Mexican",
    #     spicy=SpiceLevel.MILD,
    #     difficulty=DifficultyLevel.EASY,
    #     description="This healthy chicken taco soup gives you all the flavor of a taco in a quick and easy soup! Chicken breast, fresh veggies, and warming spices all come together to make a filling meal.",
    #     nutritional_info="Per serving: 375 cal",
    #     ingredients=[
    #         Condiment("Avocado or coconut oil", "for cooking", Measurement(Fraction(1, 2), MeasurementUnit.TBSP), None),
    #         Vegetable("Yellow onion", "diced", Measurement(1, GeneralUnit.SMALL), None),
    #         Vegetable("Red bell pepper", "diced", Measurement(1, GeneralUnit.SMALL), None),
    #         Vegetable("Green bell pepper", "diced", Measurement(1, GeneralUnit.SMALL), None),
    #         Spice("Garlic", "minced", Measurement(5, GeneralUnit.CLOVES), None),
    #         Meat("Chicken breast", "boneless, skinless", UnitConverter.convert(Measurement(1, MeasurementUnit.LB)), None),
    #         Spice("Salt", "plus more to taste", Measurement(1.5, MeasurementUnit.TSP), None),
    #         Spice("Dried oregano", "regular", Measurement(1, MeasurementUnit.TSP), None),
    #         Spice("Chipotle powder", "regular", Measurement(1, MeasurementUnit.TSP), None),
    #         Spice("Paprika", "regular", Measurement(1, MeasurementUnit.TSP), None),
    #         Spice("Cumin", "regular", Measurement(2, MeasurementUnit.TSP), None),
    #         Spice("Black pepper", "regular", Measurement(Fraction(1, 5), MeasurementUnit.TSP), None),
    #         Other("Fire roasted diced tomatoes", "canned", Measurement(1, "15 oz can"), None),  # Special case
    #         Other("Low sodium black beans", "canned, drained and rinsed", Measurement(1, "15 oz can"), None),  # Special case
    #         Vegetable("Green chilies", "canned", Measurement(2, "4.5 oz cans"), None),
    #         Condiment("Lime juice", "fresh", UnitConverter.convert(Measurement(Fraction(1, 4), MeasurementUnit.CUP)), None),
    #         Other("Low sodium chicken broth", "regular", UnitConverter.convert(Measurement(32, MeasurementUnit.OZ)), None),
    #         Vegetable("Corn", "fresh or frozen", UnitConverter.convert(Measurement(1, MeasurementUnit.CUP)), None),
    #         Vegetable("Cilantro", "chopped, for serving", None, None),
    #         Other("Sour cream or Greek yogurt", "for serving", None, None),
    #         Vegetable("Red onion", "diced, for serving", None, None),
    #         Other("Lime wedges", "for serving", None, None),
    #         Other("Shredded cheddar", "for serving", None, None)
    #     ],
    #     recipe={
    #         1: "Heat a large pot over medium high heat. Once hot, add in the avocado or coconut oil. Next, add the diced peppers, onion, and minced garlic to the pot. Sauté for 3 4 minutes until the onions start to become translucent.",
    #         2: "Add the chicken breast, canned tomatoes, black beans, canned green chilies, spices, lime juice, and chicken broth to the pot. Stir until well combined. Bring the soup to a rolling boil and then reduce the heat to a simmer. Allow the soup to simmer for 15 20 minutes or until the chicken is fully cooked.",
    #         3: "Remove the chicken breast from the soup and transfer to a plate. Use two forks to shred the chicken.",
    #         4: "Add the shredded chicken back to the soup along with the corn and stir until well combined. Let simmer for 2 3 minutes until the corn is heated through.",
    #         5: "Serve the soup with all your favorite toppings and enjoy!"
    #     }
    # ),
    Dish(
        title="Chicken Zucchini Stir Fry",
        image_url="chicken_zucchini_stir_fry.png",
        category=[Category("Dinner"), Category("Lunch")],
        time=20,
        budget_friendly=None,
        region="Asian",
        spicy=SpiceLevel.NO_SPICE,
        difficulty=DifficultyLevel.EASY,
        description="This quick Chicken and Zucchini Stir Fry is made with chicken breast, zucchini, and an easy stir fry sauce.",
        nutritional_info="Per serving: 242 cal, 6.5 g fat, 28 g protein, 17 g carbs",
        ingredients=[
            Condiment("Soy sauce", "low sodium or gluten free", UnitConverter.convert(Measurement(Fraction(1, 4), MeasurementUnit.CUP)), None),
            Other("Chicken broth", "regular", UnitConverter.convert(Measurement(1, MeasurementUnit.CUP)), None),
            Other("Cornstarch", "regular", Measurement(1, MeasurementUnit.TBSP), None),
            Condiment("Mirin", "regular", Measurement(2, MeasurementUnit.TBSP), None),
            Spice("Sugar", "regular", Measurement(1, MeasurementUnit.TBSP), None),
            Condiment("Sesame oil", "regular", Measurement(2, MeasurementUnit.TSP), None),
            Condiment("Canola oil", "divided", Measurement(1, MeasurementUnit.TBSP), None),
            Spice("Garlic", "minced", Measurement(1, MeasurementUnit.TBSP), None),
            Spice("Ginger", "minced", Measurement(1, MeasurementUnit.TBSP), None),
            Meat("Chicken breast", "sliced very thinly", UnitConverter.convert(Measurement(1, MeasurementUnit.LB)), None),
            Vegetable("Zucchini", "cut into 1/4 inch thick half moons", UnitConverter.convert(Measurement(2, MeasurementUnit.CUP)), None),
            Other("Sesame seeds", "for garnish", None, None),
            Vegetable("Scallion", "for garnish", None, None)
        ],
        recipe={
            1: "In a large bowl, add the soy sauce, chicken broth, cornstarch, mirin, sugar, and sesame oil and whisk until everything is completely dissolved.",
            2: "In a large skillet, add one teaspoon canola oil on medium high heat and cook half the chicken until just cooked through, about 2 3 minutes on each side. Set aside on a plate.",
            3: "Repeat with the second half of the chicken and an additional teaspoon of oil. Remove the chicken to the plate.",
            4: "Add the remaining 1 teaspoon oil, garlic, and ginger and cook for 30 45 seconds until very fragrant but not browned.",
            5: "Stir the garlic and ginger well and add in the sauce, whisking well. Cook the sauce for 1 minute, then add in the zucchini and cook for 2 minutes more, until thickened and the zucchini is tender crisp. Remove from heat, add in the chicken and stir well to coat. Garnish with sesame seeds and scallions if desired."
        }
    ),
    # Dish(
    #     title="Egg Roll in a Bowl",
    #     image_url="egg_roll_in_a_bowl.png",
    #     category=[Category("Low Carb"), Category("Dinner"), Category("Lunch")],
    #     time=28,
    #     budget_friendly=None,
    #     region="Asian",
    #     spicy=SpiceLevel.MILD,
    #     difficulty=DifficultyLevel.EASY,
    #     description="This egg roll in a bowl recipe is one of my favorite low carb meals. It's packed with protein and veggies, made in one skillet and comes together in less than 30 minutes!",
    #     nutritional_info="Per serving: 242 cal, 28g protein, 17g carbs, 6.5g fat",
    #     ingredients=[
    #         Meat("Ground turkey or chicken", "regular", UnitConverter.convert(Measurement(1, MeasurementUnit.LB)), None),
    #         Vegetable("Yellow onion", "chopped", UnitConverter.convert(Measurement(Fraction(1, 4), MeasurementUnit.CUP)), None),
    #         Spice("Garlic", "minced", Measurement(3, GeneralUnit.CLOVES), None),
    #         Spice("Fresh ginger", "grated or minced", Measurement(2, MeasurementUnit.TSP), None),
    #         Condiment("Toasted sesame oil", "regular", Measurement(2, MeasurementUnit.TSP), None),
    #         Vegetable("Coleslaw mix", "regular", Measurement(1, "12 14 oz package"), None), # Special case
    #         Condiment("Low sodium soy sauce, tamari or coconut aminos", "regular", UnitConverter.convert(Measurement(Fraction(1, 4), MeasurementUnit.CUP)), None),
    #         Spice("Sriracha or sambal oelek", "regular", Measurement(Fraction(1, 2), MeasurementUnit.TSP), None),
    #         Vegetable("Green onions", "sliced", Measurement(2, GeneralUnit.WHOLE), None),
    #         Spice("Sriracha", "for serving (optional)", None, None),
    #         Other("Sesame seeds", "for garnish", None, None),
    #         Vegetable("Chopped cilantro", "for garnish", None, None),
    #         Other("Cooked cauliflower rice", "for serving (optional)", None, None)
    #     ],
    #     recipe={
    #         1: "Heat a large skillet over medium high heat. Add ground meat and cook until no longer pink, about 5 6 minutes. While cooking, break meat into smaller pieces using a wooden spoon or spatula and season liberally with salt and pepper. Remove from heat and transfer to a bowl or plate.",
    #         2: "In the same skillet, over medium heat, add sesame oil. Once hot, add onion, garlic and ginger and cook until fragrant, about 3 5 minutes. Add coleslaw mix into the skillet. Toss and add soy sauce and sriracha or sambal. Cook for another 3 5 minutes or until cabbage is tender.",
    #         3: "Add cooked meat back to the pan and toss to combine. Taste and add more soy sauce or sriracha, if needed.",
    #         4: "Portion mixture into bowls and top with green onions, sesame seeds and cilantro. Serve with additional soy sauce or sriracha, if desired."
    #     }
    # ),
    Dish(
        title="Chipotle Chicken Tostadas with Pineapple Salsa",
        image_url="chipotle_chicken_tostadas.png",
        category=[Category("Dinner"), Category("Mexican")],
        time=45,
        budget_friendly=None,
        region="Mexican",
        spicy=SpiceLevel.MILD,
        difficulty=DifficultyLevel.EASY,
        description="Delicious chipotle chicken tostadas topped with a colorful, fresh pineapple salsa. These healthy chicken tostadas are easy to make and have an incredible sweet and savory flavor from chipotle chicken, sweet pineapple, creamy avocado and a kick of heat from jalapeño. A fun and flavorful weeknight dinner!",
        nutritional_info="Per serving: 462 cal, 26.8g carbohydrates, 31.8g protein, 26.7g fat, 6.3g saturated fat, 7g fiber, 7.1g sugar",
        ingredients=[
            # For the pineapple salsa
            Vegetable("Pineapple", "small diced fresh", UnitConverter.convert(Measurement(2, MeasurementUnit.CUP)), None),
            Vegetable("Red onion", "finely diced", UnitConverter.convert(Measurement(Fraction(1, 4), MeasurementUnit.CUP)), None),
            Vegetable("Jalapeño", "finely diced", Measurement(1, MeasurementUnit.TBSP), None),
            Condiment("Lime juice", "fresh", Measurement(2, MeasurementUnit.TBSP), None),
            Spice("Garlic", "minced", Measurement(1, GeneralUnit.CLOVES), None),
            Vegetable("Cilantro", "finely chopped fresh", Measurement(1, MeasurementUnit.TBSP), None),
            Condiment("Avocado oil", "or olive oil", Measurement(1, MeasurementUnit.TSP), None),
            Spice("Salt", "Pinch", None, None),
            # For the chipotle chicken
            Condiment("Avocado oil", "or olive oil", Measurement(1, MeasurementUnit.TBSP), None),
            Meat("Ground chicken", "regular", UnitConverter.convert(Measurement(2, MeasurementUnit.LB)), None),
            Spice("Chipotle chili powder", "regular", Measurement(2, MeasurementUnit.TSP), None),
            Spice("Salt", "to taste", None, None),
            Spice("Pepper", "to taste", None, None),
            Other("Chicken broth", "low sodium", UnitConverter.convert(Measurement(Fraction(1, 4), MeasurementUnit.CUP)), None),
            Other("Tomato paste", "regular", Measurement(1, MeasurementUnit.TBSP), None),
            # To assemble
            Other("Grain free tortillas", "6 (8 inch), can use Siete tortillas", None, None),
            Vegetable("Avocados", "mashed", Measurement(2, GeneralUnit.WHOLE), None),
            Vegetable("Purple cabbage", "shredded", UnitConverter.convert(Measurement(Fraction(1, 2), MeasurementUnit.CUP)), None),
            Vegetable("Cilantro", "chopped fresh",  UnitConverter.convert(Measurement(Fraction(1, 4), MeasurementUnit.CUP)), None)
        ],
        recipe={
            1: "Preheat the oven to 350 degrees F and line a baking sheet with parchment paper.",
            2: "Make the pineapple salsa: in a medium bowl, toss together the pineapple, onion, jalapeño, lime juice, garlic, cilantro, avocado oil, and salt. Refrigerate until ready to serve, up to 5 days.",
            3: "Make the chicken: in a large skillet, heat the avocado oil over medium high heat. Add the ground chicken, chipotle chili powder, salt, and pepper.",
            4: "Cook the chicken, breaking up the meat with the back of a spoon until it is brown, about 7 minutes. Drain off any excess fat from the pan, if necessary.",
            5: "Reduce the heat to medium and add the chicken broth and tomato paste and stir to combine. Continue to cook for about 2 more minutes.",
            6: "Remove from heat and cover to keep warm until ready to serve.",
            7: "To assemble: place the tortillas in a single layer on the prepared baking sheet. Lightly spray the tops of tortillas with nonstick cooking spray. Bake for 8 to 10 minutes, or until golden brown and crisp.",
            8: "Carefully spread the mashed avocado on top of each crisp tortilla. Sprinkle with the shredded cabbage and a big scoop of chipotle chicken. Top with the pineapple salsa and a sprinkle of cilantro."
        }
    ),
    # Dish(
    #     title="Spinach Garlic Parmesan Orzo with Crispy Bacon",
    #     image_url="spinach_garlic_parmesan_orzo.png",
    #     category=[Category("Dinner"), Category("Pasta")],
    #     time=30,
    #     budget_friendly=None,
    #     region="Italian",
    #     spicy=SpiceLevel.NO_SPICE,
    #     difficulty=DifficultyLevel.EASY,
    #     description="Easy, flavorful spinach garlic parmesan orzo pasta with crispy bacon and gorgeous veggies like red bell pepper, corn, carrots, and spinach. This creamy garlic parmesan orzo recipe comes together in 30 minutes, is the perfect meal prep dinner, and is delicious hot or cold!",
    #     nutritional_info="Per serving: 436 cal, 20.2g protein, 62.7g carbohydrates, 13.3g fat, 6.2g saturated fat, 4.5g fiber, 2.6g sugar",
    #     ingredients=[
    #         Meat("Bacon", "slices", Measurement(8, GeneralUnit.SLICES), None),
    #         Other("Orzo pasta", "uncooked",  UnitConverter.convert(Measurement(10, MeasurementUnit.OZ)), None),
    #         Other("Reserved pasta water", "after pasta is done boiling",  UnitConverter.convert(Measurement(Fraction(1, 2), MeasurementUnit.CUP)), None),
    #         Condiment("Butter", "unsalted", Measurement(1, MeasurementUnit.TBSP), None),
    #         Spice("Garlic", "finely minced", Measurement(3, GeneralUnit.CLOVES), None),
    #         Vegetable("Shredded carrots", "or carrots cut into matchsticks",  UnitConverter.convert(Measurement(Fraction(1, 2), MeasurementUnit.CUP)), None),
    #         Vegetable("Frozen or fresh sweet corn", "regular",  UnitConverter.convert(Measurement(Fraction(2, 3), MeasurementUnit.CUP)), None),
    #         Vegetable("Red bell pepper", "cut into chunks", Measurement(1, GeneralUnit.WHOLE), None),
    #         Vegetable("Spinach", "organic", Measurement(1, "5 oz package"), None), # Special case
    #         Dairy("Parmesan cheese", "freshly grated", UnitConverter.convert(Measurement(Fraction(1, 2), MeasurementUnit.CUP)), None),
    #         Spice("Garlic powder", "regular", Measurement(Fraction(1, 2), MeasurementUnit.TSP), None),
    #         Spice("Red chili pepper flakes", "plus more if desired", Measurement(Fraction(1, 2), MeasurementUnit.TSP), None),
    #         Spice("Salt", "to taste", None, None),
    #         Spice("Pepper", "freshly ground, to taste", None, None),
    #         Other("Flat leaf parsley", "fresh, for garnish", None, None),
    #         Other("Extra parmesan cheese", "for garnish", None, None),
    #         Vegetable("Corn", "fresh, for garnish", None, None),
    #         Meat("Bacon", "cooked, for garnish", None, None)
    #     ],
    #     recipe={
    #         1: "Add bacon to a large skillet or pan and place over medium heat, cook bacon on both sides until crispy and golden brown. If the pan starts to smoke at any point, simply lower the heat. Always cook bacon on medium low heat. Once bacon is done, blot with a paper towel to absorb excess grease, then chop into bite sized pieces and set aside.",
    #         2: "While the bacon is cooking, place a large pot of water over high heat and add in a generous amount of salt. Once water boils, stir in the orzo and cook until al dente, about 7 9 minutes. Once orzo is done cooking, drain pasta and set aside in the colander. Make sure to reserve 1/2 cup of the pasta water.",
    #         3: "Next, add 1 tablespoon butter to the same pot you cooked the pasta in and place over medium heat. Once butter is melted, add in minced garlic, carrot, corn, and red bell pepper and saute for 2 minutes.",
    #         4: "Next, add in spinach; cooking until the spinach wilts, about 2 minutes. Add the cooked orzo back into the pot and turn the heat to low. Stir in the reserved pasta water, parmesan, garlic powder, and red chili pepper flakes.",
    #         5: "Finally, stir in bacon crumbles. Add salt and pepper to taste. Optionally, add a lot of black pepper to give it a nice flavor. If you think it needs a little extra parmesan cheese, feel free to stir in 1/4 cup more. Enjoy. Serves 4."
    #     }
    # )
]
