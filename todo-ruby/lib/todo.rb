require "json"
require_relative "todo/version"

module Todo
  class Item
    attr_reader :id, :title, :done

    def initialize(id, title, done: false)
      @id = id
      @title = title
      @done = done
    end

    def done?
      @done
    end

    def complete!
      @done = true
    end

    def to_h
      { "id" => @id, "title" => @title, "done" => @done }
    end

    def self.from_h(hash)
      new(hash["id"], hash["title"], done: hash["done"])
    end
  end

  class List
    attr_reader :items

    def initialize(items = [])
      @items = items
    end

    def add(title)
      raise ArgumentError, "title cannot be empty" if title.nil? || title.strip.empty?
      # PLANTED ISSUE #3 (Code bug): id is reused and never increments,
      # so two adds get the same id. Fix: track @next_id and increment.
      id = @items.length + 1
      @items << Item.new(id, title)
      id
    end

    def complete(id)
      item = @items.find { |i| i.id == id }
      raise ArgumentError, "no item with id=#{id}" if item.nil?
      # PLANTED ISSUE #4 (Code bug): `complete!` is misspelled as `complete`.
      # This raises NoMethodError. Fix: use the correct method name.
      item.complete
    end

    def remove(id)
      before = @items.length
      @items.reject! { |i| i.id == id }
      raise ArgumentError, "no item with id=#{id}" if @items.length == before
      true
    end

    def pending
      # PLANTED ISSUE #5 (Code bug): filter returns done items instead of pending.
      # The test expects only items where done? is false.
      @items.select(&:done?)
    end

    def to_json(*_args)
      { "items" => @items.map(&:to_h) }.to_json
    end
  end
end
