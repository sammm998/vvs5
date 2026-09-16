"""En PDF kan rita mer än den visar, och det som klippts bort är ingen meter.

CAD-exporten lägger ut hela underlaget och klipper sedan bort det som ligger utanför planens ram. Det
bortklippta ligger kvar i filen som fullvärdig geometri - rätt lager, rätt penna, rätt längd - och läsningen
mätte det som rör. På ett av utvecklingsbladen är 15,8 % av bläcket sådant, och flera hundra av de dolda
vägarna ligger på rörlager.

Det svåra är inte att skära. Det svåra är att veta VILKEN klippbana som gäller för en viss väg, och två
näraliggande fel gör att synlig geometri ser dold ut - vilket vore ett värre fel än det vi rättar, för då
raderas rör som finns. Båda proven nedan är sådana som föll när bindningen togs fram:

  * en fyrhörning skrivs ul, ur, ll, lr; läser man punkterna i den ordningen får man en rosett som korsar sig
    själv med area noll, och buffer(0) "lagar" den till en fjärdedel av rätt yta;
  * varje delbana är en egen ring, och slås deras punkter ihop till en enda ring blir resultatet nonsens.

Provet arbetar på geometrin, inte på en viss ritning: inga koordinater ur data/ och inget filnamn.
"""
from vvs_engine.geometry.core import Seg
from vvs_engine.pdf.extract import _Clip, _rect_clip


def _rect_ring(x0, y0, x1, y1):
    return [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]


def test_a_stroke_outside_the_clip_has_no_visible_length():
    """Kärnan: det som ligger utanför ramen mäts inte."""
    clip = _Clip([_rect_ring(0, 0, 100, 100)])
    assert clip.visible(Seg(150, 150, 160, 160)) == []
    assert clip.outside_box((150, 150, 160, 160)) is True


def test_a_stroke_across_the_edge_keeps_only_its_visible_part():
    """Halva sträckan innanför ger halva längden - inte hela, och inte noll."""
    clip = _Clip([_rect_ring(0, 0, 100, 100)])
    parts = clip.visible(Seg(50, 50, 150, 50))
    assert len(parts) == 1
    assert abs(parts[0].length - 50.0) < 1e-6
    assert abs(parts[0].x0 - 50.0) < 1e-6 and abs(parts[0].x1 - 100.0) < 1e-6


def test_a_stroke_wholly_inside_is_untouched_and_takes_the_cheap_path():
    clip = _Clip([_rect_ring(0, 0, 100, 100)])
    assert clip.contains_box((10, 10, 90, 90)) is True
    parts = clip.visible(Seg(10, 10, 90, 90))
    assert len(parts) == 1 and abs(parts[0].length - Seg(10, 10, 90, 90).length) < 1e-6


def test_a_diagonal_edge_is_not_its_bounding_box():
    """Provfallets form: punkten ligger inom klippets bbox men utanför dess sneda kant.

    Det är precis det som gör att ett `scissor`-prov släpper igenom dold geometri.
    """
    clip = _Clip([[(0.0, 0.0), (100.0, 0.0), (0.0, 100.0)]])      # triangel, bbox 0,0-100,100
    inside_box_outside_shape = Seg(80.0, 80.0, 95.0, 95.0)
    assert clip.outside_box(inside_box_outside_shape.bbox()) is False     # bbox-provet säger "kanske"
    assert clip.visible(inside_box_outside_shape) == []                   # formen säger nej
    assert clip.visible(Seg(5.0, 5.0, 20.0, 20.0))                        # men innanför kanten syns den


def test_a_quad_is_read_in_corner_order_not_as_a_bowtie():
    """ul, ur, lr, ll - inte ul, ur, ll, lr. Den andra ordningen ger en rosett med noll area."""
    quad = _Clip([[(0.0, 0.0), (100.0, 0.0), (100.0, 100.0), (0.0, 100.0)]])
    bowtie = _Clip([[(0.0, 0.0), (100.0, 0.0), (0.0, 100.0), (100.0, 100.0)]])
    assert abs(quad.poly.area - 10000.0) < 1e-6
    # rosetten är inte kvadraten: det är just den skillnaden som gjorde synlig geometri dold
    assert bowtie.poly is None or bowtie.poly.area < 0.6 * quad.poly.area


def test_several_subpaths_are_separate_rings_not_one():
    """Två skilda rektanglar är två ytor. Slås deras punkter ihop till en ring blir ytan mellan dem 'innanför'."""
    two = _Clip([_rect_ring(0, 0, 10, 10), _rect_ring(90, 90, 100, 100)])
    assert abs(two.poly.area - 200.0) < 1e-6
    assert two.visible(Seg(40, 40, 60, 60)) == []          # mellanrummet hör inte till klippet


def test_the_rectangle_fast_path_agrees_with_the_polygon():
    """Rektangelvägen finns för att den är billig, inte för att den får svara annorlunda."""
    rect = (10.0, 10.0, 90.0, 90.0)
    poly = _Clip([[(10.0, 10.0), (90.0, 10.0), (90.0, 90.0), (10.0, 90.0), (10.0, 50.0)]])
    for seg in (Seg(0, 50, 100, 50), Seg(50, 0, 50, 100), Seg(20, 20, 80, 80), Seg(0, 0, 5, 5)):
        fast = _rect_clip(seg, rect)
        slow = poly.visible(seg)
        assert len(fast) == len(slow)
        for a, b in zip(fast, slow):
            assert abs(a.length - b.length) < 1e-6


def test_a_tangent_touch_is_not_a_length():
    """En sträcka som bara nuddar kanten har ingen synlig längd."""
    clip = _Clip([_rect_ring(0, 0, 100, 100)])
    assert all(p.length > 0 for p in clip.visible(Seg(0, 100, 100, 100)))
